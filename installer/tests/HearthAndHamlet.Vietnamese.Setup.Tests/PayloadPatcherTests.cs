using System.Diagnostics;
using System.Text;
using HearthAndHamlet.Vietnamese.Setup;
using Xunit;

namespace HearthAndHamlet.Vietnamese.Setup.Tests;

public sealed class PayloadPatcherTests
{
    [Fact]
    public async Task PatchAsync_invokes_zstd_decompress_patch_from_with_explicit_output_and_without_force()
    {
        using var root = new TempRoot();
        var recorder = Path.Combine(root.Path, "recorder.cmd");
        var argsLog = Path.Combine(root.Path, "args.txt");
        var source = Path.Combine(root.Path, "source.pck");
        var delta = Path.Combine(root.Path, "payload.patch.zst");
        var output = Path.Combine(root.Path, "out.pck");
        await File.WriteAllTextAsync(source, "source");
        await File.WriteAllTextAsync(delta, "delta");
        await File.WriteAllTextAsync(recorder, $"""
@echo off
> "{argsLog}" echo %*
exit /b 0
""");

        await new PayloadPatcher(recorder, delta).PatchAsync(source, output, CancellationToken.None);

        var args = await File.ReadAllTextAsync(argsLog);
        Assert.Contains("-d", args);
        Assert.Contains("--long=30", args);
        Assert.Contains("--patch-from", args);
        Assert.Contains(source, args);
        Assert.Contains(delta, args);
        Assert.Contains("-o", args);
        Assert.Contains(output, args);
        var tokens = args.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        Assert.DoesNotContain("-f", tokens);
        Assert.DoesNotContain("--force", tokens);
    }

    private sealed class TempRoot : IDisposable
    {
        public TempRoot()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "hnh-payload-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path);
        }

        public string Path { get; }

        public void Dispose()
        {
            try
            {
                if (Directory.Exists(Path))
                    Directory.Delete(Path, recursive: true);
            }
            catch
            {
            }
        }
    }
}
