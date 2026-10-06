using System.Security.Cryptography;
using System.Text.Json;

namespace HearthAndHamlet.Vietnamese.Setup;

public interface IInstallFileMover
{
    void Move(string source, string destination);
}

public sealed class InstallEngine
{
    private readonly InstallFingerprints _fingerprints;
    private readonly IInstallFileMover _fileMover;

    public InstallEngine(InstallFingerprints? fingerprints = null, IInstallFileMover? fileMover = null)
    {
        _fingerprints = fingerprints ?? ReleaseConstants.Fingerprints;
        _fileMover = fileMover ?? new PhysicalInstallFileMover();
    }

    public async Task<InstallResult> InstallAsync(
        GamePaths game,
        string backupRoot,
        IPayloadPatcher patcher,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(game);
        ArgumentNullException.ThrowIfNull(patcher);
        if (string.IsNullOrWhiteSpace(backupRoot))
            return Failure("invalid_backup_root", "Thư mục backup không hợp lệ.");

        FileStream? exeLock = null;
        string? backupDirectory = null;
        string? stagedPath = null;
        string? rollbackPath = null;
        var recoveryRequired = false;
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            exeLock = OpenExecutableLock(game.Executable);
            var exeHash = await HashFileAsync(game.Executable, cancellationToken);
            if (!HashEquals(exeHash, _fingerprints.ExecutableSha256))
                return Failure("unsupported_exe", "EXE game không đúng fingerprint được hỗ trợ.");

            var currentHash = await HashFileAsync(game.Pck, cancellationToken);
            if (HashEquals(currentHash, _fingerprints.TranslatedPckSha256))
                return Failure("already_installed", "Bản Việt hóa đã được cài.");
            if (!HashEquals(currentHash, _fingerprints.OriginalPckSha256))
                return Failure("unsupported_pck", "PCK hiện tại không phải bản gốc được hỗ trợ.");
            if (IsReadOnly(game.Pck))
                return Failure("write_failed", "PCK hiện tại chỉ đọc, không thể thay thế.");

            backupDirectory = CreateBackupDirectory(backupRoot);
            var backupPck = Path.Combine(backupDirectory, ReleaseConstants.BackupPckFileName);
            File.Copy(game.Pck, backupPck, overwrite: false);
            await WriteMetadataAsync(backupDirectory, exeHash, currentHash, cancellationToken);

            stagedPath = CreateTemporaryPath(game.GameDirectory, ".hnh-vi-stage-");
            try
            {
                await patcher.PatchAsync(game.Pck, stagedPath, cancellationToken);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception exception)
            {
                return Failure("patch_failed", $"Không thể tạo PCK bản Việt hóa: {exception.Message}");
            }

            if (!File.Exists(stagedPath))
                return Failure("patch_failed", "Patcher không tạo ra file PCK.");
            var stagedHash = await HashFileAsync(stagedPath, cancellationToken);
            if (!HashEquals(stagedHash, _fingerprints.TranslatedPckSha256))
                return Failure("verification_failed", "Hash PCK bản Việt hóa không khớp.");

            rollbackPath = CreateTemporaryPath(game.GameDirectory, ".hnh-vi-rollback-");
            ReplaceWithRollback(game.Pck, stagedPath, rollbackPath);
            stagedPath = null;
            var installedHash = await HashFileAsync(game.Pck, cancellationToken);
            if (!HashEquals(installedHash, _fingerprints.TranslatedPckSha256))
            {
                try
                {
                    RestoreRollback(game.Pck, rollbackPath);
                    rollbackPath = null;
                }
                catch (Exception exception)
                {
                    recoveryRequired = true;
                    return Failure(
                        "recovery_required",
                        $"Không thể rollback an toàn ({exception.Message}). Giữ file rollback và backup; cần phục hồi thủ công: {rollbackPath}",
                        backupDirectory,
                        installedHash);
                }
                return Failure("verification_failed", "Hash sau khi thay PCK không khớp; đã rollback.");
            }

            DeleteIfExists(rollbackPath);
            rollbackPath = null;
            return new InstallResult(true, "installed", "Đã cài bản Việt hóa.", backupDirectory, installedHash);
        }
        catch (OperationCanceledException)
        {
            return Failure("cancelled", "Thao tác đã bị hủy.");
        }
        catch (RecoveryRequiredException exception)
        {
            recoveryRequired = true;
            return Failure("recovery_required", exception.Message, backupDirectory);
        }
        catch (FileNotFoundException exception)
        {
            return Failure("missing_file", $"Thiếu file game: {exception.FileName ?? exception.Message}");
        }
        catch (UnauthorizedAccessException exception)
        {
            return Failure("write_failed", $"Không có quyền ghi thư mục game: {exception.Message}");
        }
        catch (IOException exception)
        {
            return Failure("write_failed", $"Không thể thay đổi file game: {exception.Message}");
        }
        finally
        {
            exeLock?.Dispose();
            if (!recoveryRequired)
            {
                DeleteIfExists(stagedPath);
                DeleteIfExists(rollbackPath);
            }
            // A failed install must not leave an apparently usable backup behind.
            if (!recoveryRequired && backupDirectory is not null && (!File.Exists(game.Pck) || !IsTranslated(game.Pck)))
                CleanupFailedBackup(backupDirectory, backupRoot);
        }
    }

    public async Task<InstallResult> RestoreAsync(
        GamePaths game,
        string backupRoot,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(game);
        if (string.IsNullOrWhiteSpace(backupRoot))
            return Failure("invalid_backup_root", "Thư mục backup không hợp lệ.");

        FileStream? exeLock = null;
        string? stagedPath = null;
        string? rollbackPath = null;
        var recoveryRequired = false;
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            exeLock = OpenExecutableLock(game.Executable);
            var exeHash = await HashFileAsync(game.Executable, cancellationToken);
            if (!HashEquals(exeHash, _fingerprints.ExecutableSha256))
                return Failure("unsupported_exe", "EXE game không đúng fingerprint được hỗ trợ.");

            var currentHash = await HashFileAsync(game.Pck, cancellationToken);
            if (!HashEquals(currentHash, _fingerprints.TranslatedPckSha256))
                return Failure("unsupported_pck", "PCK hiện tại không phải bản Việt hóa được hỗ trợ.");
            if (IsReadOnly(game.Pck))
                return Failure("write_failed", "PCK hiện tại chỉ đọc, không thể phục hồi.");

            var backup = await FindValidBackupAsync(backupRoot, cancellationToken);
            if (backup is null)
                return Failure("backup_missing", "Không tìm thấy backup hợp lệ để phục hồi.");

            stagedPath = CreateTemporaryPath(game.GameDirectory, ".hnh-vi-restore-");
            File.Copy(backup.PckPath, stagedPath, overwrite: false);
            var stagedHash = await HashFileAsync(stagedPath, cancellationToken);
            if (!HashEquals(stagedHash, _fingerprints.OriginalPckSha256))
                return Failure("backup_invalid", "Hash backup không khớp.");

            rollbackPath = CreateTemporaryPath(game.GameDirectory, ".hnh-vi-rollback-");
            ReplaceWithRollback(game.Pck, stagedPath, rollbackPath);
            stagedPath = null;
            var restoredHash = await HashFileAsync(game.Pck, cancellationToken);
            if (!HashEquals(restoredHash, _fingerprints.OriginalPckSha256))
            {
                try
                {
                    RestoreRollback(game.Pck, rollbackPath);
                    rollbackPath = null;
                }
                catch (Exception exception)
                {
                    recoveryRequired = true;
                    return Failure(
                        "recovery_required",
                        $"Không thể rollback an toàn ({exception.Message}). Giữ file rollback để phục hồi thủ công: {rollbackPath}",
                        backup.Directory,
                        restoredHash);
                }
                return Failure("verification_failed", "Hash sau khi phục hồi không khớp; đã rollback.");
            }

            DeleteIfExists(rollbackPath);
            rollbackPath = null;
            return new InstallResult(true, "restored", "Đã phục hồi bản gốc.", backup.Directory, restoredHash);
        }
        catch (OperationCanceledException)
        {
            return Failure("cancelled", "Thao tác đã bị hủy.");
        }
        catch (RecoveryRequiredException exception)
        {
            recoveryRequired = true;
            return Failure("recovery_required", exception.Message);
        }
        catch (FileNotFoundException exception)
        {
            return Failure("missing_file", $"Thiếu file game hoặc backup: {exception.FileName ?? exception.Message}");
        }
        catch (UnauthorizedAccessException exception)
        {
            return Failure("write_failed", $"Không có quyền ghi thư mục game: {exception.Message}");
        }
        catch (IOException exception)
        {
            return Failure("write_failed", $"Không thể thay đổi file game: {exception.Message}");
        }
        finally
        {
            exeLock?.Dispose();
            if (!recoveryRequired)
            {
                DeleteIfExists(stagedPath);
                DeleteIfExists(rollbackPath);
            }
        }
    }

    private async Task<BackupInfo?> FindValidBackupAsync(string backupRoot, CancellationToken cancellationToken)
    {
        var buildRoot = Path.Combine(backupRoot, ReleaseConstants.BuildId);
        if (!Directory.Exists(buildRoot))
            return null;

        IEnumerable<string> directories;
        try { directories = Directory.EnumerateDirectories(buildRoot).OrderByDescending(Directory.GetLastWriteTimeUtc); }
        catch (IOException) { return null; }
        foreach (var directory in directories)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var metadataPath = Path.Combine(directory, ReleaseConstants.BackupMetadataFileName);
            var pckPath = Path.Combine(directory, ReleaseConstants.BackupPckFileName);
            try
            {
                await using var stream = File.OpenRead(metadataPath);
                var metadata = await JsonSerializer.DeserializeAsync<BackupMetadata>(stream, cancellationToken: cancellationToken);
                if (metadata is null ||
                    metadata.BuildId != ReleaseConstants.BuildId ||
                    metadata.GameVersion != ReleaseConstants.GameVersion ||
                    !HashEquals(metadata.OriginalPckSha256, _fingerprints.OriginalPckSha256) ||
                    !HashEquals(metadata.ExecutableSha256, _fingerprints.ExecutableSha256) ||
                    !HashEquals(metadata.TranslatedPckSha256, _fingerprints.TranslatedPckSha256) ||
                    !File.Exists(pckPath))
                    continue;
                var pckHash = await HashFileAsync(pckPath, cancellationToken);
                if (HashEquals(pckHash, _fingerprints.OriginalPckSha256))
                    return new BackupInfo(directory, pckPath);
            }
            catch (JsonException) { }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        return null;
    }

    private async Task WriteMetadataAsync(string directory, string executableHash, string originalHash, CancellationToken cancellationToken)
    {
        var metadata = new BackupMetadata
        {
            BuildId = ReleaseConstants.BuildId,
            GameVersion = ReleaseConstants.GameVersion,
            ExecutableSha256 = executableHash,
            OriginalPckSha256 = originalHash,
            TranslatedPckSha256 = _fingerprints.TranslatedPckSha256,
            CreatedUtc = DateTimeOffset.UtcNow
        };
        var path = Path.Combine(directory, ReleaseConstants.BackupMetadataFileName);
        await using var stream = File.Create(path);
        await JsonSerializer.SerializeAsync(stream, metadata, cancellationToken: cancellationToken);
    }

    private FileStream OpenExecutableLock(string path) =>
        new(path, FileMode.Open, FileAccess.Read, FileShare.Read);

    private static string CreateBackupDirectory(string backupRoot)
    {
        var buildRoot = Path.Combine(Path.GetFullPath(backupRoot), ReleaseConstants.BuildId);
        Directory.CreateDirectory(buildRoot);
        var directory = Path.Combine(buildRoot, DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ"));
        for (var attempt = 0; Directory.Exists(directory); attempt++)
            directory = Path.Combine(buildRoot, $"{DateTime.UtcNow:yyyyMMddTHHmmssfffZ}-{attempt + 1}");
        Directory.CreateDirectory(directory);
        return directory;
    }

    private static string CreateTemporaryPath(string directory, string prefix) =>
        Path.Combine(directory, prefix + Guid.NewGuid().ToString("N") + ".tmp");

    private void ReplaceWithRollback(string current, string staged, string rollback)
    {
        _fileMover.Move(current, rollback);
        try
        {
            _fileMover.Move(staged, current);
        }
        catch
        {
            try
            {
                if (!File.Exists(current) && File.Exists(rollback))
                {
                    _fileMover.Move(rollback, current);
                    if (!File.Exists(current) || File.Exists(rollback))
                        throw new IOException("The rollback move did not produce a single recoverable file.");
                }
                else if (File.Exists(current))
                    throw new IOException("The replacement state is ambiguous.");
                else
                    throw new IOException("Neither the current file nor the rollback file is available.");
            }
            catch (Exception recoveryException)
            {
                throw new RecoveryRequiredException(
                    $"Không thể thay PCK và không thể phục hồi tự động ({recoveryException.Message}). Giữ rollback để phục hồi thủ công: {rollback}",
                    recoveryException);
            }
            throw;
        }
    }

    private void RestoreRollback(string current, string rollback)
    {
        DeleteIfExists(current);
        _fileMover.Move(rollback, current);
        if (!File.Exists(current) || File.Exists(rollback))
            throw new IOException("The rollback move did not produce a single recoverable file.");
    }

    private static async Task<string> HashFileAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, 1024 * 64, FileOptions.SequentialScan);
        return Convert.ToHexString(await SHA256.HashDataAsync(stream, cancellationToken));
    }

    private bool IsTranslated(string path)
    {
        try { return HashEquals(HashFileAsync(path, CancellationToken.None).GetAwaiter().GetResult(), _fingerprints.TranslatedPckSha256); }
        catch { return false; }
    }

    private static bool IsReadOnly(string path)
    {
        try { return (File.GetAttributes(path) & FileAttributes.ReadOnly) != 0; }
        catch { return false; }
    }

    private static bool HashEquals(string? actual, string expected) =>
        actual is not null && string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase);

    private static InstallResult Failure(string code, string message, string? backupDirectory = null, string? targetHash = null) =>
        new(false, code, message, backupDirectory, targetHash);

    private static void DeleteIfExists(string? path)
    {
        if (path is null) return;
        try { if (File.Exists(path)) File.Delete(path); } catch { }
    }

    private static void DeleteDirectoryIfExists(string? path)
    {
        if (path is null) return;
        try { if (Directory.Exists(path)) Directory.Delete(path, recursive: true); } catch { }
    }

    private static void CleanupFailedBackup(string backupDirectory, string backupRoot)
    {
        DeleteDirectoryIfExists(backupDirectory);
        var buildRoot = Path.Combine(Path.GetFullPath(backupRoot), ReleaseConstants.BuildId);
        try
        {
            if (Directory.Exists(buildRoot) && !Directory.EnumerateFileSystemEntries(buildRoot).Any())
                Directory.Delete(buildRoot);
            if (Directory.Exists(backupRoot) && !Directory.EnumerateFileSystemEntries(backupRoot).Any())
                Directory.Delete(backupRoot);
        }
        catch { }
    }

    private sealed class BackupMetadata
    {
        public string BuildId { get; set; } = string.Empty;
        public string GameVersion { get; set; } = string.Empty;
        public string ExecutableSha256 { get; set; } = string.Empty;
        public string OriginalPckSha256 { get; set; } = string.Empty;
        public string TranslatedPckSha256 { get; set; } = string.Empty;
        public DateTimeOffset CreatedUtc { get; set; }
    }

    private sealed record BackupInfo(string Directory, string PckPath);

    private sealed class RecoveryRequiredException(string message, Exception innerException) : IOException(message, innerException);

    private sealed class PhysicalInstallFileMover : IInstallFileMover
    {
        public void Move(string source, string destination) => File.Move(source, destination);
    }
}
