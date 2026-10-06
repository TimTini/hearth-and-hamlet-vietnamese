using System.Text.Json.Serialization;

namespace HearthAndHamlet.Vietnamese.Setup;

internal sealed class BackupMetadata
{
    public string BuildId { get; set; } = string.Empty;
    public string GameVersion { get; set; } = string.Empty;
    public string ExecutableSha256 { get; set; } = string.Empty;
    public string OriginalPckSha256 { get; set; } = string.Empty;
    public string TranslatedPckSha256 { get; set; } = string.Empty;
    public DateTimeOffset CreatedUtc { get; set; }
}

[JsonSerializable(typeof(BackupMetadata))]
internal partial class BackupMetadataJsonContext : JsonSerializerContext;
