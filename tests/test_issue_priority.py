#!/usr/bin/env python3
"""
TDD: issue_priority.py のテストスイート

失敗パターンから先に定義し、実装を駆動する。

テスト対象:
  - parse_priority(text: str) -> str
  - build_prompt(title: str, body: str) -> str
  - is_bot_edit(sender: str) -> bool
  - get_priority_from_claude(title: str, body: str) -> str  [外部API]
  - remove_priority_labels(issue_number: str, repo: str) -> None  [外部コマンド]
  - add_priority_label(issue_number: str, repo: str, priority: str) -> None  [外部コマンド]
  - main() -> None  [統合]
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import issue_priority
from issue_priority import (
    DEFAULT_PRIORITY,
    VALID_PRIORITIES,
    add_priority_label,
    build_prompt,
    get_priority_from_claude,
    is_bot_edit,
    parse_priority,
    remove_priority_labels,
)


# ===========================================================================
# TestParsePriority: レスポンス解析の失敗パターン
# ===========================================================================


class TestParsePriority:
    """parse_priority() - Claudeのレスポンスから優先度を抽出"""

    # --- 失敗パターン（RED先行） ---

    def test_invalid_p5_falls_back_to_default(self):
        """存在しないP5はデフォルト(P3)にフォールバック"""
        assert parse_priority("P5") == DEFAULT_PRIORITY

    def test_empty_string_falls_back_to_default(self):
        """空文字列はP3にフォールバック"""
        assert parse_priority("") == DEFAULT_PRIORITY

    def test_whitespace_only_falls_back_to_default(self):
        """空白のみはP3にフォールバック"""
        assert parse_priority("   ") == DEFAULT_PRIORITY

    def test_garbage_text_falls_back_to_default(self):
        """無関係な文章はP3にフォールバック"""
        assert parse_priority("I cannot determine the priority") == DEFAULT_PRIORITY

    def test_none_string_falls_back_to_default(self):
        """'None'/'null' 文字列はP3にフォールバック"""
        assert parse_priority("None") == DEFAULT_PRIORITY
        assert parse_priority("null") == DEFAULT_PRIORITY

    def test_priority_with_explanation_extracts_priority(self):
        """'P2 because it is a bug' → P2を抽出"""
        assert parse_priority("P2 because it is a bug") == "P2"

    def test_lowercase_priority_normalized_to_upper(self):
        """小文字 'p1' → 'P1' に正規化"""
        assert parse_priority("p1") == "P1"
        assert parse_priority("p4") == "P4"

    def test_priority_with_leading_trailing_whitespace(self):
        """前後空白を除去して正しく返す"""
        assert parse_priority("  P1  ") == "P1"

    def test_priority_with_newline(self):
        """末尾改行を含む場合でも正しく抽出"""
        assert parse_priority("P3\n") == "P3"

    def test_priority_embedded_in_long_text(self):
        """長い説明文の中からP2を抽出"""
        assert parse_priority("Based on the analysis, this is P2 priority") == "P2"

    # --- 正常パターン ---

    @pytest.mark.parametrize("priority", ["P1", "P2", "P3", "P4"])
    def test_valid_priorities_returned_as_is(self, priority):
        """P1〜P4はそのまま返す"""
        assert parse_priority(priority) == priority

    def test_default_priority_is_p3(self):
        """デフォルトはP3"""
        assert DEFAULT_PRIORITY == "P3"

    def test_valid_priorities_are_p1_to_p4(self):
        """有効な優先度はP1〜P4の4種類"""
        assert set(VALID_PRIORITIES) == {"P1", "P2", "P3", "P4"}


# ===========================================================================
# TestBuildPrompt: プロンプト生成の失敗パターン
# ===========================================================================


class TestBuildPrompt:
    """build_prompt() - Claudeへ送るプロンプトを生成"""

    def test_none_body_does_not_raise(self):
        """bodyがNoneでもクラッシュしない"""
        prompt = build_prompt("Test title", None)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_empty_body_does_not_raise(self):
        """bodyが空文字でもクラッシュしない"""
        prompt = build_prompt("Test title", "")
        assert isinstance(prompt, str)

    def test_long_body_is_truncated(self):
        """2000文字超のbodyはトランケートされる"""
        long_body = "a" * 10000
        prompt = build_prompt("Test", long_body)
        # 連続2001文字のaはプロンプト内に現れない
        assert "a" * 2001 not in prompt

    def test_prompt_contains_title(self):
        """プロンプトにタイトルが含まれる"""
        prompt = build_prompt("Critical Login Bug", "body text")
        assert "Critical Login Bug" in prompt

    def test_prompt_contains_all_priority_definitions(self):
        """プロンプトにP1〜P4の定義が含まれる"""
        prompt = build_prompt("title", "body")
        for p in ["P1", "P2", "P3", "P4"]:
            assert p in prompt

    def test_prompt_instructs_single_word_output(self):
        """Claudeに1単語のみ出力させる指示が含まれる"""
        prompt = build_prompt("title", "body")
        assert any(
            word in prompt
            for word in ["1単語", "one word", "1 word", "のみ", "only"]
        )

    def test_body_with_double_quotes_does_not_break_prompt(self):
        """bodyにダブルクォートが含まれてもプロンプトが壊れない"""
        body = 'He said "critical bug" in production'
        prompt = build_prompt("title", body)
        assert isinstance(prompt, str)

    def test_body_with_backticks_does_not_break_prompt(self):
        """bodyにバッククォートが含まれても壊れない"""
        body = "Use `gh issue edit` command"
        prompt = build_prompt("title", body)
        assert isinstance(prompt, str)


# ===========================================================================
# TestIsBotEdit: botループ防止の失敗パターン
# ===========================================================================


class TestIsBotEdit:
    """is_bot_edit() - github-actions[bot]の編集を検出"""

    def test_bot_sender_returns_true(self):
        """github-actions[bot]はTrueを返す"""
        assert is_bot_edit("github-actions[bot]") is True

    def test_human_sender_returns_false(self):
        """人間のユーザーはFalseを返す"""
        assert is_bot_edit("miyashita337") is False

    def test_empty_sender_returns_false(self):
        """空文字はFalse（KeyErrorではない）"""
        assert is_bot_edit("") is False

    def test_partial_bot_name_returns_false(self):
        """'github-actions'（[]なし）はFalse（完全一致のみ）"""
        assert is_bot_edit("github-actions") is False

    def test_bot_name_with_extra_space_returns_false(self):
        """前後スペース付きはFalse（厳密一致）"""
        assert is_bot_edit(" github-actions[bot] ") is False

    def test_dependabot_returns_false(self):
        """dependabot[bot]はFalse（github-actions[bot]のみ対象）"""
        assert is_bot_edit("dependabot[bot]") is False


# ===========================================================================
# TestRemovePriorityLabels: ghコマンド失敗パターン
# ===========================================================================


class TestRemovePriorityLabels:
    """remove_priority_labels() - P1〜P4ラベルを全除去"""

    @patch("subprocess.run")
    def test_calls_gh_exactly_four_times(self, mock_run):
        """P1〜P4の4つ全てにghコマンドを呼ぶ"""
        mock_run.return_value = MagicMock(returncode=0)
        remove_priority_labels("42", "owner/repo")
        assert mock_run.call_count == 4

    @patch("subprocess.run")
    def test_label_not_exist_does_not_raise(self, mock_run):
        """ghがexit 1（ラベル未存在）を返しても例外を上げない"""
        mock_run.return_value = MagicMock(returncode=1)
        # 例外が上がらないことを確認
        remove_priority_labels("42", "owner/repo")

    @patch("subprocess.run")
    def test_uses_correct_issue_number(self, mock_run):
        """指定したissue番号でghを呼ぶ"""
        mock_run.return_value = MagicMock(returncode=0)
        remove_priority_labels("99", "owner/repo")
        for c in mock_run.call_args_list:
            args = c[0][0]
            assert "99" in args

    @patch("subprocess.run")
    def test_uses_correct_repo(self, mock_run):
        """指定したリポジトリ名でghを呼ぶ"""
        mock_run.return_value = MagicMock(returncode=0)
        remove_priority_labels("1", "myorg/myrepo")
        for c in mock_run.call_args_list:
            args = c[0][0]
            assert "myorg/myrepo" in args

    @patch("subprocess.run")
    def test_uses_remove_label_flag(self, mock_run):
        """--remove-label フラグを使う"""
        mock_run.return_value = MagicMock(returncode=0)
        remove_priority_labels("1", "owner/repo")
        for c in mock_run.call_args_list:
            args = c[0][0]
            assert "--remove-label" in args

    @patch("subprocess.run")
    def test_all_four_priorities_removed(self, mock_run):
        """P1,P2,P3,P4が全て除去対象になっている"""
        mock_run.return_value = MagicMock(returncode=0)
        remove_priority_labels("1", "owner/repo")
        removed_labels = set()
        for c in mock_run.call_args_list:
            args = c[0][0]
            idx = args.index("--remove-label")
            removed_labels.add(args[idx + 1])
        assert removed_labels == {"P1", "P2", "P3", "P4"}


# ===========================================================================
# TestAddPriorityLabel: ghコマンド失敗パターン
# ===========================================================================


class TestAddPriorityLabel:
    """add_priority_label() - 優先度ラベルを付与"""

    @patch("subprocess.run")
    def test_success_calls_gh_once(self, mock_run):
        """正常時はghコマンドを1回だけ呼ぶ"""
        mock_run.return_value = MagicMock(returncode=0)
        add_priority_label("42", "owner/repo", "P2")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_gh_failure_raises_called_process_error(self, mock_run):
        """ghがエラーを返した場合はCalledProcessErrorを上げる"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
        with pytest.raises(subprocess.CalledProcessError):
            add_priority_label("42", "owner/repo", "P2")

    @patch("subprocess.run")
    def test_uses_add_label_flag_with_correct_priority(self, mock_run):
        """--add-label フラグと正しい優先度を使う"""
        mock_run.return_value = MagicMock(returncode=0)
        add_priority_label("42", "owner/repo", "P1")
        args = mock_run.call_args[0][0]
        assert "--add-label" in args
        assert "P1" in args

    @patch("subprocess.run")
    def test_uses_correct_issue_number_and_repo(self, mock_run):
        """正しいissue番号とリポジトリを使う"""
        mock_run.return_value = MagicMock(returncode=0)
        add_priority_label("77", "testorg/testrepo", "P3")
        args = mock_run.call_args[0][0]
        assert "77" in args
        assert "testorg/testrepo" in args


# ===========================================================================
# TestGetPriorityFromClaude: Claude API呼び出し失敗パターン
# ===========================================================================


class TestGetPriorityFromClaude:
    """get_priority_from_claude() - Claude APIでpriority判定"""

    def test_missing_api_key_raises(self):
        """ANTHROPIC_API_KEYが未設定の場合はKeyError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises((KeyError, Exception)):
                get_priority_from_claude("title", "body")

    @patch("issue_priority.anthropic.Anthropic")
    def test_api_returns_valid_priority(self, mock_cls):
        """APIが正常にP2を返す場合"""
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text="P2")]
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = get_priority_from_claude("Login bug", "Users cannot login")
        assert result == "P2"

    @patch("issue_priority.anthropic.Anthropic")
    def test_api_returns_invalid_falls_back_to_p3(self, mock_cls):
        """APIが不正値を返した場合はparse_priorityがP3にフォールバック"""
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text="I cannot determine")
        ]
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = get_priority_from_claude("Some issue", "body")
        assert result == "P3"

    @patch("issue_priority.anthropic.Anthropic")
    def test_api_error_propagates(self, mock_cls):
        """API通信エラーは例外として伝播する"""
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API timeout")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with pytest.raises(Exception, match="API timeout"):
                get_priority_from_claude("title", "body")

    @patch("issue_priority.anthropic.Anthropic")
    def test_uses_haiku_model_for_cost(self, mock_cls):
        """コスト削減のためclaude-haiku系モデルを使う"""
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text="P3")]
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            get_priority_from_claude("title", "body")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "haiku" in call_kwargs.get("model", "")

    @patch("issue_priority.anthropic.Anthropic")
    def test_max_tokens_is_small(self, mock_cls):
        """P1〜P4のみ返せばよいのでmax_tokensは小さい値（<=32）"""
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text="P1")]
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            get_priority_from_claude("title", "body")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs.get("max_tokens", 999) <= 32


# ===========================================================================
# TestMain: 統合テスト - 失敗パターン優先
# ===========================================================================

FAKE_EVENT_BOT = {
    "sender": {"login": "github-actions[bot]"},
    "issue": {"number": 42, "title": "Test", "body": "body"},
}

FAKE_EVENT_HUMAN = {
    "sender": {"login": "miyashita337"},
    "issue": {"number": 42, "title": "Critical bug", "body": "App crashes"},
}

FAKE_EVENT_NO_BODY = {
    "sender": {"login": "miyashita337"},
    "issue": {"number": 10, "title": "No body issue", "body": None},
}

BASE_ENV = {
    "ANTHROPIC_API_KEY": "test-key",
    "GITHUB_TOKEN": "gh-token",
    "GITHUB_REPOSITORY": "owner/repo",
}


class TestMain:
    """main() - 統合テスト"""

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_BOT)
    def test_bot_edit_skips_claude_api(self, mock_event):
        """bot編集の場合はClaude APIを呼ばない"""
        with patch.dict(os.environ, BASE_ENV):
            with patch("issue_priority.get_priority_from_claude") as mock_claude:
                issue_priority.main()
                mock_claude.assert_not_called()

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_HUMAN)
    def test_missing_api_key_exits_with_nonzero(self, mock_event):
        """ANTHROPIC_API_KEYが未設定の場合はSystemExit"""
        env = {k: v for k, v in BASE_ENV.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                issue_priority.main()
            assert exc_info.value.code != 0

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_HUMAN)
    @patch("issue_priority.add_priority_label")
    @patch("issue_priority.remove_priority_labels")
    @patch("issue_priority.get_priority_from_claude", return_value="P2")
    def test_normal_flow_removes_then_adds(
        self, mock_claude, mock_remove, mock_add, mock_event
    ):
        """正常フロー: ラベル除去 → 新ラベル追加の順序"""
        with patch.dict(os.environ, BASE_ENV):
            issue_priority.main()
        mock_remove.assert_called_once_with("42", "owner/repo")
        mock_add.assert_called_once_with("42", "owner/repo", "P2")

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_HUMAN)
    @patch("issue_priority.add_priority_label")
    @patch("issue_priority.remove_priority_labels")
    @patch("issue_priority.get_priority_from_claude", return_value="P1")
    def test_calls_with_correct_issue_number(
        self, mock_claude, mock_remove, mock_add, mock_event
    ):
        """issue番号が正しくghコマンドに渡される"""
        with patch.dict(os.environ, BASE_ENV):
            issue_priority.main()
        mock_remove.assert_called_once_with("42", "owner/repo")
        mock_add.assert_called_once_with("42", "owner/repo", "P1")

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_NO_BODY)
    @patch("issue_priority.add_priority_label")
    @patch("issue_priority.remove_priority_labels")
    @patch("issue_priority.get_priority_from_claude", return_value="P3")
    def test_none_body_issue_does_not_crash(
        self, mock_claude, mock_remove, mock_add, mock_event
    ):
        """issue.bodyがNullでもクラッシュしない"""
        with patch.dict(os.environ, BASE_ENV):
            issue_priority.main()
        mock_add.assert_called_once()

    @patch("issue_priority.get_event_data", return_value=FAKE_EVENT_HUMAN)
    @patch("issue_priority.add_priority_label")
    @patch("issue_priority.remove_priority_labels")
    @patch(
        "issue_priority.get_priority_from_claude",
        side_effect=subprocess.CalledProcessError(1, "gh"),
    )
    def test_add_label_failure_propagates(
        self, mock_claude, mock_remove, mock_add, mock_event
    ):
        """ラベル追加失敗は例外として伝播する"""
        with patch.dict(os.environ, BASE_ENV):
            with pytest.raises(subprocess.CalledProcessError):
                issue_priority.main()
