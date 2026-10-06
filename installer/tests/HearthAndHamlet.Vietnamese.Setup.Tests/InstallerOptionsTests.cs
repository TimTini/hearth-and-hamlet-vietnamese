using HearthAndHamlet.Vietnamese.Setup;
using Xunit;

namespace HearthAndHamlet.Vietnamese.Setup.Tests;

public sealed class InstallerOptionsTests
{
    [Fact]
    public void Parse_reads_explicit_game_dir_and_install_switches()
    {
        var options = InstallerOptions.Parse([
            "--game-dir", "C:\\Trò chơi\\Hearth and Hamlet",
            "--install", "--yes", "--no-pause"]);

        Assert.Equal("C:\\Trò chơi\\Hearth and Hamlet", options.GameDirectory);
        Assert.True(options.Install);
        Assert.False(options.Restore);
        Assert.True(options.Yes);
        Assert.True(options.NoPause);
    }

    [Fact]
    public void Parse_reads_restore_switch()
    {
        var options = InstallerOptions.Parse(["--restore"]);

        Assert.False(options.Install);
        Assert.True(options.Restore);
    }

    [Fact]
    public void Parse_rejects_conflicting_actions_and_unknown_options()
    {
        Assert.Throws<ArgumentException>(() => InstallerOptions.Parse(["--install", "--restore"]));
        Assert.Throws<ArgumentException>(() => InstallerOptions.Parse(["--wat"]));
    }
}
