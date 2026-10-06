using System.Diagnostics;
using System.Reflection;

namespace HearthAndHamlet.Vietnamese.Setup;

public interface IPayloadPatcher
{
    Task PatchAsync(string sourcePck, string outputPck, CancellationToken cancellationToken);
}

public sealed class PayloadPatcher : IPayloadPatcher
{
    private readonly string? _zstdPath;
    private readonly string? _deltaPath;

    public PayloadPatcher(string? zstdPath = null, string? deltaPath = null)
    {
        _zstdPath = zstdPath;
        _deltaPath = deltaPath;
    }

    public async Task PatchAsync(string sourcePck, string outputPck, CancellationToken cancellationToken)
    {
        string? ownedTempRoot = null;
        try
        {
            ownedTempRoot = _zstdPath is null || _deltaPath is null
                ? Path.Combine(Path.GetTempPath(), "HearthAndHamletVietnamese", "payload-" + Guid.NewGuid().ToString("N"))
                : null;
            if (ownedTempRoot is not null)
                Directory.CreateDirectory(ownedTempRoot);
            var zstdPath = _zstdPath ?? ResolveResource("zstd.exe", ownedTempRoot!);
            var deltaPath = _deltaPath ?? ResolveResource("payload.patch.zst", ownedTempRoot!);
            var startInfo = new ProcessStartInfo
            {
                FileName = zstdPath,
                UseShellExecute = false,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            startInfo.ArgumentList.Add("--patch-from");
            startInfo.ArgumentList.Add(sourcePck);
            startInfo.ArgumentList.Add(deltaPath);
            startInfo.ArgumentList.Add(outputPck);

            using var process = Process.Start(startInfo) ?? throw new InvalidOperationException("Could not start the embedded patcher.");
            try
            {
                await process.WaitForExitAsync(cancellationToken);
            }
            catch
            {
                try
                {
                    if (!process.HasExited)
                        process.Kill(entireProcessTree: true);
                }
                catch { }
                throw;
            }
            if (process.ExitCode != 0)
            {
                var error = await process.StandardError.ReadToEndAsync(cancellationToken);
                throw new InvalidOperationException($"The embedded patcher failed with exit code {process.ExitCode}: {error.Trim()}");
            }
        }
        finally
        {
            if (ownedTempRoot is not null)
            {
                try { if (Directory.Exists(ownedTempRoot)) Directory.Delete(ownedTempRoot, recursive: true); } catch { }
            }
        }
    }

    private static string ResolveResource(string suffix, string tempRoot)
    {
        var assembly = Assembly.GetExecutingAssembly();
        var resourceName = assembly.GetManifestResourceNames()
            .FirstOrDefault(name => name.EndsWith(suffix, StringComparison.OrdinalIgnoreCase));
        if (resourceName is null)
            throw new InvalidOperationException("Installer payload is not embedded in this build.");

        var output = Path.Combine(tempRoot, suffix);
        using var input = assembly.GetManifestResourceStream(resourceName)
            ?? throw new InvalidOperationException("Installer payload resource could not be read.");
        using var file = File.Create(output);
        input.CopyTo(file);
        return output;
    }
}
