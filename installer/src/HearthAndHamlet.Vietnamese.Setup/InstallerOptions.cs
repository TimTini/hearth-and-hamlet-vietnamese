namespace HearthAndHamlet.Vietnamese.Setup;

public sealed class InstallerOptions
{
    public string? GameDirectory { get; private init; }
    public string? BackupRoot { get; private init; }
    public bool Install { get; private init; }
    public bool Restore { get; private init; }
    public bool Yes { get; private init; }
    public bool NoPause { get; private init; }
    public bool Help { get; private init; }

    public static InstallerOptions Parse(string[] args)
    {
        ArgumentNullException.ThrowIfNull(args);

        string? gameDirectory = null;
        string? backupRoot = null;
        var install = false;
        var restore = false;
        var yes = false;
        var noPause = false;
        var help = false;

        for (var i = 0; i < args.Length; i++)
        {
            var arg = args[i];
            switch (arg)
            {
                case "--install":
                    install = true;
                    break;
                case "--restore":
                    restore = true;
                    break;
                case "--yes":
                    yes = true;
                    break;
                case "--no-pause":
                    noPause = true;
                    break;
                case "--help":
                case "-h":
                case "/?":
                    help = true;
                    break;
                case "--game-dir":
                    gameDirectory = ReadValue(args, ref i, arg);
                    break;
                case "--backup-root":
                    backupRoot = ReadValue(args, ref i, arg);
                    break;
                default:
                    if (arg.StartsWith("--game-dir=", StringComparison.Ordinal))
                        gameDirectory = ReadInlineValue(arg, "--game-dir=");
                    else if (arg.StartsWith("--backup-root=", StringComparison.Ordinal))
                        backupRoot = ReadInlineValue(arg, "--backup-root=");
                    else
                        throw new ArgumentException($"Unknown option: {arg}", nameof(args));
                    break;
            }
        }

        if (install && restore)
            throw new ArgumentException("--install and --restore cannot be used together.", nameof(args));

        return new InstallerOptions
        {
            GameDirectory = gameDirectory,
            BackupRoot = backupRoot,
            Install = install || !restore,
            Restore = restore,
            Yes = yes,
            NoPause = noPause,
            Help = help
        };
    }

    private static string ReadValue(string[] args, ref int index, string option)
    {
        if (++index >= args.Length || string.IsNullOrWhiteSpace(args[index]))
            throw new ArgumentException($"{option} requires a value.", nameof(args));
        return args[index];
    }

    private static string ReadInlineValue(string arg, string prefix)
    {
        var value = arg[prefix.Length..];
        if (string.IsNullOrWhiteSpace(value))
            throw new ArgumentException($"{prefix.TrimEnd('=')} requires a value.", nameof(arg));
        return value;
    }
}
