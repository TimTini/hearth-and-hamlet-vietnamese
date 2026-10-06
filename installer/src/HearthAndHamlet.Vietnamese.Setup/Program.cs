namespace HearthAndHamlet.Vietnamese.Setup;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        InstallerOptions options;
        try
        {
            options = InstallerOptions.Parse(args);
        }
        catch (ArgumentException exception)
        {
            Console.Error.WriteLine($"Tham số không hợp lệ: {exception.Message}");
            return ReleaseConstants.UsageExitCode;
        }

        if (options.Help)
        {
            PrintUsage();
            return Finish(ReleaseConstants.SuccessExitCode, options.NoPause);
        }

        var gameDirectory = options.GameDirectory;
        if (string.IsNullOrWhiteSpace(gameDirectory))
        {
            var candidate = GameLocator.FindCandidates(
                AppContext.BaseDirectory,
                Environment.CurrentDirectory,
                GameLocator.GetSteamRoots()).FirstOrDefault();
            gameDirectory = candidate;
        }

        if (string.IsNullOrWhiteSpace(gameDirectory))
        {
            Console.Error.WriteLine("Không tự tìm thấy game. Hãy dùng --game-dir <thư mục Hearth and Hamlet>.");
            return Finish(ReleaseConstants.GameNotFoundExitCode, options.NoPause);
        }

        var game = new GamePaths(gameDirectory);
        Console.WriteLine($"Thư mục game: {game.GameDirectory}");
        Console.WriteLine(options.Restore ? "Hành động: phục hồi bản gốc" : "Hành động: cài bản Việt hóa");
        if (!options.Yes)
        {
            Console.Write("Tiếp tục? [y/N] ");
            if (!string.Equals(Console.ReadLine()?.Trim(), "y", StringComparison.OrdinalIgnoreCase))
                return Finish(ReleaseConstants.RejectedExitCode, options.NoPause);
        }

        var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if (string.IsNullOrWhiteSpace(localAppData))
        {
            Console.Error.WriteLine("Không xác định được LOCALAPPDATA để lưu backup.");
            return Finish(ReleaseConstants.OperationFailedExitCode, options.NoPause);
        }
        var backupRoot = options.BackupRoot ?? Path.Combine(localAppData, "HearthAndHamletVietnamese", "backups");
        InstallResult result;
        try
        {
            var engine = new InstallEngine();
            result = options.Restore
                ? await engine.RestoreAsync(game, backupRoot, CancellationToken.None)
                : await engine.InstallAsync(game, backupRoot, new PayloadPatcher(), CancellationToken.None);
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine($"Thao tác thất bại: {exception.Message}");
            return Finish(ReleaseConstants.OperationFailedExitCode, options.NoPause);
        }

        Console.WriteLine(result.Message);
        if (result.Success)
            return Finish(ReleaseConstants.SuccessExitCode, options.NoPause);
        Console.Error.WriteLine($"Mã lỗi: {result.Code}");
        return Finish(result.Code switch
        {
            "unsupported_exe" or "unsupported_pck" or "already_installed" or "backup_missing" or "backup_invalid" => ReleaseConstants.RejectedExitCode,
            _ => ReleaseConstants.OperationFailedExitCode
        }, options.NoPause);
    }

    private static void PrintUsage()
    {
        Console.WriteLine("Hearth and Hamlet - Trình cài bản Việt hóa");
        Console.WriteLine("  --install                 Cài bản Việt hóa (mặc định)");
        Console.WriteLine("  --restore                 Phục hồi PCK gốc từ backup");
        Console.WriteLine("  --game-dir <path>         Chỉ định thư mục game");
        Console.WriteLine("  --backup-root <path>      Chỉ định thư mục backup");
        Console.WriteLine("  --yes                     Bỏ qua xác nhận");
        Console.WriteLine("  --no-pause                Không chờ ở cuối chương trình");
    }

    private static int Finish(int code, bool noPause)
    {
        if (!noPause && !Console.IsInputRedirected)
        {
            Console.Write("Nhấn Enter để kết thúc...");
            Console.ReadLine();
        }
        return code;
    }
}
