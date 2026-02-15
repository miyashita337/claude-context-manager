#!/usr/bin/env raku

use lib 'lib';
use WinMac::Main;

sub MAIN {
    my $app = WinMac::Main.new;
    $app.run;
}
