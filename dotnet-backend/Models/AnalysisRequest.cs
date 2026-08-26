namespace FinExtractAgent.Api.Models
{
    public class AuditAnalysisResult
    {
        public string Status { get; set; } = "success";
        public string RiskBadge { get; set; } = "High Confidence";
        public Dictionary<string, object>? ExtractedData { get; set; }
        public List<string>? GuardrailFlags { get; set; }
    }

    public class HealthCheckResponse
    {
        public string Status { get; set; } = "Healthy";
        public string Service { get; set; } = ".NET Core Financial Gateway API";
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    }
}
