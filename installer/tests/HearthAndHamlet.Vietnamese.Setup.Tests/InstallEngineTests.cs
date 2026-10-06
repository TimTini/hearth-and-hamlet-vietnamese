using System.Security.Cryptography;
using HearthAndHamlet.Vietnamese.Setup;
using Xunit;

namespace HearthAndHamlet.Vietnamese.Setup.Tests;

public sealed class InstallEngineTests
{
    [Fact]
    public async Task InstallAsync_creates_verified_backup_and_replaces_original_pck()
    {
        using var fixture = new GameFixture("original");
        var patcher = new WritingPatcher("translated");

        var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, patcher, CancellationToken.None);

        Assert.True(result.Success, result.Message);
        Assert.Equal("translated", await File.ReadAllTextAsync(fixture.Game.PckPath));
        Assert.NotNull(result.BackupDirectory);
        Assert.Equal(fixture.OriginalHash, await HashAsync(Path.Combine(result.BackupDirectory!, ReleaseConstants.PckFileName)));
        Assert.DoesNotContain(fixture.Game.GameDirectory, await File.ReadAllTextAsync(Path.Combine(result.BackupDirectory!, ReleaseConstants.BackupMetadataFileName)), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task InstallAsync_rejects_unsupported_exe_or_pck_and_does_not_create_backup()
    {
        using var fixture = new GameFixture("original");
        await File.WriteAllTextAsync(fixture.Game.ExecutablePath, "wrong exe");
        var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new WritingPatcher("translated"), CancellationToken.None);
        Assert.False(result.Success);
        Assert.Empty(Directory.Exists(fixture.BackupRoot) ? Directory.EnumerateDirectories(fixture.BackupRoot, "*", SearchOption.AllDirectories) : []);

        using var pckFixture = new GameFixture("wrong pck");
        result = await new InstallEngine(pckFixture.Fingerprints).InstallAsync(pckFixture.Game, pckFixture.BackupRoot, new WritingPatcher("translated"), CancellationToken.None);
        Assert.False(result.Success);
    }

    [Fact]
    public async Task InstallAsync_reports_already_installed_without_running_patcher()
    {
        using var fixture = new GameFixture("translated");
        var patcher = new WritingPatcher("should not run");
        var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, patcher, CancellationToken.None);
        Assert.False(result.Success);
        Assert.Equal("already_installed", result.Code);
        Assert.False(patcher.WasCalled);
    }

    [Fact]
    public async Task RestoreAsync_restores_valid_backup_and_rejects_stale_current_game()
    {
        using var fixture = new GameFixture("original");
        var install = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new WritingPatcher("translated"), CancellationToken.None);
        Assert.True(install.Success, install.Message);
        var restore = await new InstallEngine(fixture.Fingerprints).RestoreAsync(fixture.Game, fixture.BackupRoot, CancellationToken.None);
        Assert.True(restore.Success, restore.Message);
        Assert.Equal("original", await File.ReadAllTextAsync(fixture.Game.PckPath));

        await File.WriteAllTextAsync(fixture.Game.PckPath, "changed");
        restore = await new InstallEngine(fixture.Fingerprints).RestoreAsync(fixture.Game, fixture.BackupRoot, CancellationToken.None);
        Assert.False(restore.Success);
        Assert.Equal("unsupported_pck", restore.Code);
    }

    [Fact]
    public async Task RestoreAsync_ignores_malformed_backup_metadata()
    {
        using var fixture = new GameFixture("original");
        var install = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new WritingPatcher("translated"), CancellationToken.None);
        Assert.True(install.Success, install.Message);
        await File.WriteAllTextAsync(Path.Combine(install.BackupDirectory!, ReleaseConstants.BackupMetadataFileName), "{ malformed");

        var restore = await new InstallEngine(fixture.Fingerprints).RestoreAsync(fixture.Game, fixture.BackupRoot, CancellationToken.None);

        Assert.False(restore.Success);
        Assert.Equal("backup_missing", restore.Code);
        Assert.Equal("translated", await File.ReadAllTextAsync(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_removes_backup_when_patch_fails()
    {
        using var fixture = new GameFixture("original");
        var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new ThrowingPatcher(), CancellationToken.None);
        Assert.False(result.Success);
        Assert.Equal("patch_failed", result.Code);
        Assert.Equal("original", await File.ReadAllTextAsync(fixture.Game.PckPath));
        Assert.False(Directory.Exists(fixture.BackupRoot) && Directory.EnumerateFileSystemEntries(fixture.BackupRoot).Any());
    }

    [Fact]
    public async Task InstallAsync_rolls_back_when_post_replace_hash_is_wrong()
    {
        using var fixture = new GameFixture("original");
        var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new WritingPatcher("bad target"), CancellationToken.None);
        Assert.False(result.Success);
        Assert.Equal("verification_failed", result.Code);
        Assert.Equal("original", await File.ReadAllTextAsync(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_preserves_recovery_files_when_move_back_fails()
    {
        using var fixture = new GameFixture("original");
        var result = await new InstallEngine(fixture.Fingerprints, new FailRecoveryMove()).InstallAsync(
            fixture.Game,
            fixture.BackupRoot,
            new WritingPatcher("translated"),
            CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("recovery_required", result.Code);
        Assert.Contains("thủ công", result.Message, StringComparison.OrdinalIgnoreCase);
        Assert.NotNull(result.BackupDirectory);
        Assert.True(Directory.Exists(result.BackupDirectory));
        Assert.NotEmpty(Directory.EnumerateFiles(fixture.Game.GameDirectory, ".hnh-vi-rollback-*.tmp"));
        Assert.False(File.Exists(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_preserves_recovery_files_when_post_replace_hash_fails()
    {
        using var fixture = new GameFixture("original");
        var result = await new InstallEngine(
            fixture.Fingerprints,
            null,
            new FailOnHashCall(4, cancel: false)).InstallAsync(
                fixture.Game,
                fixture.BackupRoot,
                new WritingPatcher("translated"),
                CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("recovery_required", result.Code);
        Assert.Contains("rollback", result.Message, StringComparison.OrdinalIgnoreCase);
        Assert.True(Directory.Exists(result.BackupDirectory));
        Assert.NotEmpty(Directory.EnumerateFiles(fixture.Game.GameDirectory, ".hnh-vi-rollback-*.tmp"));
        Assert.Equal("translated", await File.ReadAllTextAsync(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_preserves_recovery_files_when_post_replace_hash_is_cancelled()
    {
        using var fixture = new GameFixture("original");
        using var cancellation = new CancellationTokenSource();
        var result = await new InstallEngine(
            fixture.Fingerprints,
            null,
            new FailOnHashCall(4, cancel: true, cancellation)).InstallAsync(
                fixture.Game,
                fixture.BackupRoot,
                new WritingPatcher("translated"),
                cancellation.Token);

        Assert.False(result.Success);
        Assert.Equal("recovery_required", result.Code);
        Assert.Contains("rollback", result.Message, StringComparison.OrdinalIgnoreCase);
        Assert.True(Directory.Exists(result.BackupDirectory));
        Assert.NotEmpty(Directory.EnumerateFiles(fixture.Game.GameDirectory, ".hnh-vi-rollback-*.tmp"));
        Assert.Equal("translated", await File.ReadAllTextAsync(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_preserves_recovery_files_when_first_move_reports_after_moving()
    {
        using var fixture = new GameFixture("original");
        var result = await new InstallEngine(fixture.Fingerprints, new MoveThenFail()).InstallAsync(
            fixture.Game,
            fixture.BackupRoot,
            new WritingPatcher("translated"),
            CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("recovery_required", result.Code);
        Assert.Contains("rollback", result.Message, StringComparison.OrdinalIgnoreCase);
        Assert.True(Directory.Exists(result.BackupDirectory));
        Assert.NotEmpty(Directory.EnumerateFiles(fixture.Game.GameDirectory, ".hnh-vi-rollback-*.tmp"));
        Assert.False(File.Exists(fixture.Game.PckPath));
    }

    [Fact]
    public async Task RestoreAsync_preserves_recovery_files_when_move_back_fails()
    {
        using var fixture = new GameFixture("original");
        var install = await new InstallEngine(fixture.Fingerprints).InstallAsync(
            fixture.Game,
            fixture.BackupRoot,
            new WritingPatcher("translated"),
            CancellationToken.None);
        Assert.True(install.Success, install.Message);

        var result = await new InstallEngine(fixture.Fingerprints, new FailRecoveryMove()).RestoreAsync(
            fixture.Game,
            fixture.BackupRoot,
            CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("recovery_required", result.Code);
        Assert.Contains("thủ công", result.Message, StringComparison.OrdinalIgnoreCase);
        Assert.True(Directory.Exists(install.BackupDirectory));
        Assert.NotEmpty(Directory.EnumerateFiles(fixture.Game.GameDirectory, ".hnh-vi-rollback-*.tmp"));
        Assert.False(File.Exists(fixture.Game.PckPath));
    }

    [Fact]
    public async Task InstallAsync_reports_unwritable_destination_without_mutation()
    {
        using var fixture = new GameFixture("original");
        File.SetAttributes(fixture.Game.PckPath, FileAttributes.ReadOnly);
        try
        {
            var result = await new InstallEngine(fixture.Fingerprints).InstallAsync(fixture.Game, fixture.BackupRoot, new WritingPatcher("translated"), CancellationToken.None);
            Assert.False(result.Success);
            Assert.Equal("write_failed", result.Code);
            Assert.Equal("original", await File.ReadAllTextAsync(fixture.Game.PckPath));
        }
        finally
        {
            File.SetAttributes(fixture.Game.PckPath, FileAttributes.Normal);
        }
    }

    private static async Task<string> HashAsync(string path)
    {
        await using var stream = File.OpenRead(path);
        return Convert.ToHexString(await SHA256.HashDataAsync(stream));
    }

    private sealed class WritingPatcher(string content) : IPayloadPatcher
    {
        public bool WasCalled { get; private set; }

        public async Task PatchAsync(string sourcePck, string outputPck, CancellationToken cancellationToken)
        {
            WasCalled = true;
            await File.WriteAllTextAsync(outputPck, content, cancellationToken);
        }
    }

    private sealed class ThrowingPatcher : IPayloadPatcher
    {
        public Task PatchAsync(string sourcePck, string outputPck, CancellationToken cancellationToken) =>
            Task.FromException(new InvalidOperationException("synthetic patch failure"));
    }

    private sealed class FailRecoveryMove : IInstallFileMover
    {
        private int _moveCount;

        public void Move(string source, string destination)
        {
            _moveCount++;
            if (_moveCount >= 2)
                throw new IOException("synthetic move-back failure");
            File.Move(source, destination);
        }
    }

    private sealed class MoveThenFail : IInstallFileMover
    {
        public void Move(string source, string destination)
        {
            File.Move(source, destination);
            throw new IOException("synthetic post-move failure");
        }
    }

    private sealed class FailOnHashCall(int failingCall, bool cancel, CancellationTokenSource? cancellation = null) : IInstallFileHasher
    {
        private int _callCount;

        public async Task<string> HashAsync(string path, CancellationToken cancellationToken)
        {
            if (++_callCount == failingCall)
            {
                if (cancel)
                {
                    cancellation?.Cancel();
                    throw new OperationCanceledException(cancellationToken);
                }
                throw new IOException("synthetic post-replace hash failure");
            }

            await using var stream = File.OpenRead(path);
            return Convert.ToHexString(await SHA256.HashDataAsync(stream, cancellationToken));
        }
    }

    private sealed class GameFixture : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), "hnh-setup-engine-tests", Guid.NewGuid().ToString("N"));
        public GamePaths Game { get; }
        public string BackupRoot { get; }
        public string OriginalHash { get; }
        public InstallFingerprints Fingerprints { get; }

        public GameFixture(string pckContent)
        {
            Directory.CreateDirectory(_root);
            File.WriteAllText(Path.Combine(_root, ReleaseConstants.ExecutableFileName), "exe");
            File.WriteAllText(Path.Combine(_root, ReleaseConstants.PckFileName), pckContent);
            Game = new GamePaths(_root);
            BackupRoot = Path.Combine(_root, "backups");
            var executableHash = Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes("exe")));
            OriginalHash = Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes("original")));
            var translatedHash = Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes("translated")));
            Fingerprints = new InstallFingerprints(executableHash, OriginalHash, translatedHash);
        }

        public void Dispose()
        {
            if (Directory.Exists(_root))
            {
                if (File.Exists(Game.PckPath))
                    File.SetAttributes(Game.PckPath, FileAttributes.Normal);
                Directory.Delete(_root, recursive: true);
            }
        }
    }
}
