namespace HearthAndHamlet.Vietnamese.Setup;

public static class ReleaseConstants
{
    public const string GameDirectoryName = "Hearth and Hamlet";
    public const string ExecutableFileName = "Hearth and Hamlet.exe";
    public const string PckFileName = "Hearth and Hamlet.pck";
    public const string BuildId = "25600292";
    public const string GameVersion = "1.1.0.0";
    public const string OriginalPckSha256 = "7D5A2113B5D63B40605413A70B707DC7F56AFC7DE02BCE34760E227BFE6E0201";
    public const string TranslatedPckSha256 = "BEDB9B0A788AB5547A166197FB44648F92D09E550928D769B12F919A362A7227";
    public const string ExecutableSha256 = "7D37BBF3BD6AB823F2659CE410FE792EFF2A51D1280FC211E3175C2D412F9A2A";
    public const string BackupMetadataFileName = "metadata.json";
    public const string BackupPckFileName = PckFileName;

    public const int SuccessExitCode = 0;
    public const int UsageExitCode = 2;
    public const int GameNotFoundExitCode = 3;
    public const int RejectedExitCode = 4;
    public const int OperationFailedExitCode = 5;

    public static InstallFingerprints Fingerprints { get; } = new(
        ExecutableSha256,
        OriginalPckSha256,
        TranslatedPckSha256);
}

public sealed record InstallFingerprints(
    string ExecutableSha256,
    string OriginalPckSha256,
    string TranslatedPckSha256)
{
    public static InstallFingerprints Default => ReleaseConstants.Fingerprints;
}

public sealed class GamePaths
{
    public GamePaths(string gameDirectory)
    {
        if (string.IsNullOrWhiteSpace(gameDirectory))
            throw new ArgumentException("Game directory is required.", nameof(gameDirectory));

        GameDirectory = Path.GetFullPath(gameDirectory);
        ExecutablePath = Path.Combine(GameDirectory, ReleaseConstants.ExecutableFileName);
        PckPath = Path.Combine(GameDirectory, ReleaseConstants.PckFileName);
    }

    public GamePaths(string gameDirectory, string executablePath, string pckPath)
        : this(gameDirectory)
    {
        ExecutablePath = Path.GetFullPath(executablePath);
        PckPath = Path.GetFullPath(pckPath);
    }

    public string GameDirectory { get; }
    public string ExecutablePath { get; private set; }
    public string PckPath { get; private set; }

    public string Executable => ExecutablePath;

    public string Pck => PckPath;

    // These aliases make the object convenient for callers that name paths explicitly.
    public string GameExecutablePath => Executable;
    public string GamePckPath => Pck;
}

public sealed record InstallResult(
    bool Success,
    string Code,
    string Message,
    string? BackupDirectory = null,
    string? TargetHash = null)
{
    public bool IsSuccess => Success;
}
