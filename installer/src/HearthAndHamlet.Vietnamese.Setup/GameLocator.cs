using System.Text;
using System.Globalization;
using Microsoft.Win32;

namespace HearthAndHamlet.Vietnamese.Setup;

public static class GameLocator
{
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

        foreach (var path in ParseLibraryPaths(text))
            yield return path;
    }

    private static IEnumerable<string> ParseLibraryPaths(string text)
    {
        if (text.Length > 0 && text[0] == '\uFEFF')
            text = text[1..];
        if (!TryTokenize(text, out var tokens))
            yield break;

        var position = 0;
        if (!ReadString(tokens, ref position, "libraryfolders") || !ReadToken(tokens, ref position, VdfTokenKind.Open))
            yield break;

        var paths = new List<string>();
        while (position < tokens.Count && tokens[position].Kind != VdfTokenKind.Close)
        {
            if (!ReadString(tokens, ref position, out var index) ||
                !int.TryParse(index, NumberStyles.None, CultureInfo.InvariantCulture, out var libraryIndex) ||
                libraryIndex < 0)
                yield break;
            if (!ReadToken(tokens, ref position, VdfTokenKind.Open))
                yield break;

            string? path = null;
            while (position < tokens.Count && tokens[position].Kind != VdfTokenKind.Close)
            {
                if (!ReadString(tokens, ref position, out var fieldName))
                    yield break;
                if (position >= tokens.Count)
                    yield break;
                if (tokens[position].Kind == VdfTokenKind.String)
                {
                    var value = tokens[position++].Value;
                    if (string.Equals(fieldName, "path", StringComparison.OrdinalIgnoreCase))
                        path = value;
                }
                else if (tokens[position].Kind == VdfTokenKind.Open)
                {
                    if (!SkipObject(tokens, ref position))
                        yield break;
                }
                else
                {
                    yield break;
                }
            }
            if (!ReadToken(tokens, ref position, VdfTokenKind.Close))
                yield break;
            if (!string.IsNullOrWhiteSpace(path) && Path.IsPathFullyQualified(path))
                paths.Add(path);
        }

        if (!ReadToken(tokens, ref position, VdfTokenKind.Close) || position != tokens.Count)
            yield break;
        foreach (var path in paths)
            yield return path;
    }

    private static bool TryTokenize(string text, out List<VdfToken> tokens)
    {
        tokens = [];
        for (var index = 0; index < text.Length; index++)
        {
            var character = text[index];
            if (char.IsWhiteSpace(character))
                continue;
            if (character == '{')
            {
                tokens.Add(new VdfToken(VdfTokenKind.Open, string.Empty));
                continue;
            }
            if (character == '}')
            {
                tokens.Add(new VdfToken(VdfTokenKind.Close, string.Empty));
                continue;
            }
            if (character != '"')
                return false;

            var value = new StringBuilder();
            var closed = false;
            var escaped = false;
            for (index++; index < text.Length; index++)
            {
                character = text[index];
                if (escaped)
                {
                    value.Append(character switch
                    {
                        '"' => '"',
                        '\\' => '\\',
                        'n' => '\n',
                        'r' => '\r',
                        't' => '\t',
                        _ => character
                    });
                    escaped = false;
                }
                else if (character == '\\')
                {
                    escaped = true;
                }
                else if (character == '"')
                {
                    closed = true;
                    break;
                }
                else
                {
                    value.Append(character);
                }
            }
            if (!closed || escaped)
                return false;
            tokens.Add(new VdfToken(VdfTokenKind.String, value.ToString()));
        }
        return true;
    }

    private static bool SkipObject(IReadOnlyList<VdfToken> tokens, ref int position)
    {
        if (!ReadToken(tokens, ref position, VdfTokenKind.Open))
            return false;
        while (position < tokens.Count && tokens[position].Kind != VdfTokenKind.Close)
        {
            if (!ReadString(tokens, ref position, out _))
                return false;
            if (position >= tokens.Count)
                return false;
            if (tokens[position].Kind == VdfTokenKind.String)
                position++;
            else if (tokens[position].Kind == VdfTokenKind.Open && !SkipObject(tokens, ref position))
                return false;
            else if (tokens[position].Kind != VdfTokenKind.Open)
                return false;
        }
        return ReadToken(tokens, ref position, VdfTokenKind.Close);
    }

    private static bool ReadString(IReadOnlyList<VdfToken> tokens, ref int position, string expected)
    {
        return ReadString(tokens, ref position, out var value) &&
            string.Equals(value, expected, StringComparison.OrdinalIgnoreCase);
    }

    private static bool ReadString(IReadOnlyList<VdfToken> tokens, ref int position, out string value)
    {
        if (position < tokens.Count && tokens[position].Kind == VdfTokenKind.String)
        {
            value = tokens[position++].Value;
            return true;
        }
        value = string.Empty;
        return false;
    }

    private static bool ReadToken(IReadOnlyList<VdfToken> tokens, ref int position, VdfTokenKind expected)
    {
        if (position < tokens.Count && tokens[position].Kind == expected)
        {
            position++;
            return true;
        }
        return false;
    }

    private enum VdfTokenKind { String, Open, Close }

    private readonly record struct VdfToken(VdfTokenKind Kind, string Value);
}
