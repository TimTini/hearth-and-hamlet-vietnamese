using HearthAndHamlet.Vietnamese.Setup;
using Xunit;

namespace HearthAndHamlet.Vietnamese.Setup.Tests;

public sealed class GameLocatorTests
{
    [Fact]
    public void FindCandidates_prioritizes_installer_and_current_directories_and_requires_both_game_files()
    {
        using var fixture = new TempDirectory();
        var installer = fixture.CreateDirectory("installer");
        var current = fixture.CreateDirectory("current");
        var validInstaller = fixture.CreateDirectory("installer");
        var invalidCurrent = fixture.CreateDirectory("current");
        File.WriteAllText(Path.Combine(validInstaller, "Hearth and Hamlet.exe"), "exe");
        File.WriteAllText(Path.Combine(validInstaller, "Hearth and Hamlet.pck"), "pck");
        File.WriteAllText(Path.Combine(invalidCurrent, "Hearth and Hamlet.exe"), "exe");

        var candidates = GameLocator.FindCandidates(installer, current, []).ToArray();

        Assert.Single(candidates);
        Assert.Equal(Path.GetFullPath(validInstaller), candidates[0]);
    }

    [Fact]
    public void FindCandidates_reads_unicode_space_library_from_libraryfolders_vdf()
    {
        using var fixture = new TempDirectory();
        var steamRoot = fixture.CreateDirectory("Steam Root");
        var library = fixture.CreateDirectory("Thư viện có khoảng trắng");
        var game = fixture.CreateDirectory("Thư viện có khoảng trắng", "steamapps", "common", "Hearth and Hamlet");
        File.WriteAllText(Path.Combine(game, "Hearth and Hamlet.exe"), "exe");
        File.WriteAllText(Path.Combine(game, "Hearth and Hamlet.pck"), "pck");
        var vdfPath = Path.Combine(steamRoot, "steamapps", "libraryfolders.vdf");
        Directory.CreateDirectory(Path.GetDirectoryName(vdfPath)!);
        File.WriteAllText(vdfPath, $"\"libraryfolders\" {{\n  \"0\" {{ \"path\" \"{library.Replace("\\", "\\\\")}\" }}\n}}\n");

        var candidates = GameLocator.FindCandidates("", "", [steamRoot]).ToArray();

        Assert.Contains(Path.GetFullPath(game), candidates);
    }

    [Fact]
    public void FindCandidates_ignores_malformed_vdf_and_invalid_library_candidate()
    {
        using var fixture = new TempDirectory();
        var steamRoot = fixture.CreateDirectory("Steam");
        var invalid = fixture.CreateDirectory("Steam", "steamapps", "common", "Hearth and Hamlet");
        File.WriteAllText(Path.Combine(invalid, "Hearth and Hamlet.exe"), "exe");
        var vdfPath = Path.Combine(steamRoot, "steamapps", "libraryfolders.vdf");
        Directory.CreateDirectory(Path.GetDirectoryName(vdfPath)!);
        File.WriteAllText(vdfPath, "not a vdf with an unclosed block { \"path\" \"bad\"");

        var candidates = GameLocator.FindCandidates("", "", [steamRoot]).ToArray();

        Assert.Empty(candidates);
    }

    [Fact]
    public void FindCandidates_rejects_balanced_vdf_with_non_library_structure()
    {
        using var fixture = new TempDirectory();
        var steamRoot = fixture.CreateDirectory("Steam");
        var library = fixture.CreateDirectory("Valid Library");
        var game = fixture.CreateDirectory("Valid Library", "steamapps", "common", "Hearth and Hamlet");
        File.WriteAllText(Path.Combine(game, "Hearth and Hamlet.exe"), "exe");
        File.WriteAllText(Path.Combine(game, "Hearth and Hamlet.pck"), "pck");
        var vdfPath = Path.Combine(steamRoot, "steamapps", "libraryfolders.vdf");
        Directory.CreateDirectory(Path.GetDirectoryName(vdfPath)!);
        File.WriteAllText(vdfPath,
            $"\"libraryfolders\" {{\n  \"0\" {{ \"path\" \"{library.Replace("\\", "\\\\")}\" }}\n  \"not-a-library-index\" {{ \"path\" \"{library.Replace("\\", "\\\\")}\" }}\n}}\n");

        var candidates = GameLocator.FindCandidates("", "", [steamRoot]).ToArray();

        Assert.Empty(candidates);
    }

    private sealed class TempDirectory : IDisposable
    {
        private readonly string _path = Path.Combine(Path.GetTempPath(), "hnh-setup-tests", Guid.NewGuid().ToString("N"));

        public TempDirectory() => Directory.CreateDirectory(_path);

        public string CreateDirectory(params string[] parts)
        {
            var path = parts.Aggregate(_path, Path.Combine);
            Directory.CreateDirectory(path);
            return path;
        }

        public void Dispose()
        {
            if (Directory.Exists(_path)) Directory.Delete(_path, recursive: true);
        }
    }
}
