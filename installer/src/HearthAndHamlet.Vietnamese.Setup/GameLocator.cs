using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace HearthAndHamlet.Vietnamese.Setup;

public static class GameLocator
{
    private static readonly Regex PathEntryRegex = new(
        "\\\"path\\\"\\s+\\\"(?<path>(?:\\\\.|[^\\\"\\\\])*)\\\"",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public static IEnumerable<string> FindCandidates(
        string executableDirectory,
        string currentDirectory,
        IEnumerable<string> steamRoots)
    {
        ArgumentNullException.ThrowIfNull(steamRoots);
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var root in new[] { executableDirectory, currentDirectory })
        {
            foreach (var candidate in ExpandRoot(root))
            {
                if (TryAccept(candidate, seen))
                    yield return candidate;
            }
        }

        foreach (var steamRoot in steamRoots)
        {
            foreach (var candidate in ExpandSteamRoot(steamRoot))
            {
                if (TryAccept(candidate, seen))
                    yield return candidate;
            }
        }
    }

    public static IEnumerable<string> GetSteamRoots()
    {
        var roots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        if (!string.IsNullOrEmpty(localAppData))
            roots.Add(Path.Combine(localAppData, "Steam"));
        if (!string.IsNullOrEmpty(programFiles))
            roots.Add(Path.Combine(programFiles, "Steam"));
        if (!string.IsNullOrEmpty(programFiles))
            roots.Add(Path.Combine(programFiles, "Steam", "steamapps"));
        foreach (var registryRoot in ReadRegistrySteamRoots())
            roots.Add(registryRoot);
        return roots;
    }

    private static IEnumerable<string> ReadRegistrySteamRoots()
    {
        if (!OperatingSystem.IsWindows())
            yield break;

        foreach (var hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        {
            foreach (var view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
            {
                RegistryKey? key = null;
                var values = new List<string>();
                try
                {
                    key = RegistryKey.OpenBaseKey(hive, view).OpenSubKey("Software\\Valve\\Steam");
                    if (key is null)
                        continue;
                    foreach (var valueName in new[] { "SteamPath", "InstallPath", "BaseInstallFolder_1", "BaseInstallFolder_2", "BaseInstallFolder_3" })
                    {
                        if (key.GetValue(valueName) is string path && !string.IsNullOrWhiteSpace(path))
                            values.Add(path);
                    }
                }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
                catch (System.Security.SecurityException) { }
                finally
                {
                    key?.Dispose();
                }
                foreach (var value in values)
                    yield return value;
            }
        }
    }

    private static IEnumerable<string> ExpandRoot(string? root)
    {
        if (string.IsNullOrWhiteSpace(root))
            yield break;

        yield return root;
        yield return Path.Combine(root, ReleaseConstants.GameDirectoryName);
    }

    private static IEnumerable<string> ExpandSteamRoot(string? root)
    {
        if (string.IsNullOrWhiteSpace(root))
            yield break;

        yield return root;
        yield return Path.Combine(root, "common", ReleaseConstants.GameDirectoryName);
        yield return Path.Combine(root, "steamapps", "common", ReleaseConstants.GameDirectoryName);

        var vdfPaths = new[]
        {
            Path.Combine(root, "steamapps", "libraryfolders.vdf"),
            Path.Combine(root, "libraryfolders.vdf")
        };
        foreach (var vdfPath in vdfPaths)
        {
            foreach (var library in ReadLibraryPaths(vdfPath))
            {
                yield return library;
                yield return Path.Combine(library, "steamapps", "common", ReleaseConstants.GameDirectoryName);
            }
        }
    }

    private static bool TryAccept(string path, HashSet<string> seen)
    {
        try
        {
            var fullPath = Path.GetFullPath(path);
            if (!Directory.Exists(fullPath) ||
                !File.Exists(Path.Combine(fullPath, ReleaseConstants.ExecutableFileName)) ||
                !File.Exists(Path.Combine(fullPath, ReleaseConstants.PckFileName)))
                return false;
            return seen.Add(fullPath);
        }
        catch (ArgumentException)
        {
            return false;
        }
        catch (IOException)
        {
            return false;
        }
    }

    private static IEnumerable<string> ReadLibraryPaths(string vdfPath)
    {
        string text;
        try
        {
            if (!File.Exists(vdfPath))
                yield break;
            text = File.ReadAllText(vdfPath, Encoding.UTF8);
        }
        catch (IOException)
        {
            yield break;
        }
        catch (UnauthorizedAccessException)
        {
            yield break;
        }

        if (!IsBalancedVdf(text))
            yield break;

        foreach (Match match in PathEntryRegex.Matches(text))
        {
            var path = match.Groups["path"].Value
                .Replace("\\\\", "\\", StringComparison.Ordinal)
                .Replace("\\\"", "\"", StringComparison.Ordinal);
            if (!string.IsNullOrWhiteSpace(path))
                yield return path;
        }
    }

    private static bool IsBalancedVdf(string text)
    {
        var braces = 0;
        var quoted = false;
        var escaped = false;
        foreach (var character in text)
        {
            if (escaped)
            {
                escaped = false;
                continue;
            }
            if (quoted && character == '\\')
            {
                escaped = true;
                continue;
            }
            if (character == '\"')
            {
                quoted = !quoted;
                continue;
            }
            if (quoted)
                continue;
            if (character == '{') braces++;
            if (character == '}' && --braces < 0) return false;
        }
        return !quoted && braces == 0;
    }
}
