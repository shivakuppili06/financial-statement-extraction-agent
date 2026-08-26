using Microsoft.AspNetCore.Mvc;
using FinExtractAgent.Api.Models;

namespace FinExtractAgent.Api.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class FinancialAnalysisController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;

        public FinancialAnalysisController(IHttpClientFactory httpClientFactory)
        {
            _httpClientFactory = httpClientFactory;
        }

        [HttpGet("health")]
        public IActionResult GetHealth()
        {
            return Ok(new HealthCheckResponse());
        }

        [HttpPost("analyze")]
        public async Task<IActionResult> ProxyAnalyze(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                return BadRequest(new { error = "No file uploaded." });
            }

            // Proxy file request to Python AI Microservice running on http://127.0.0.1:5000/api/analyze
            var client = _httpClientFactory.CreateClient();
            using var content = new MultipartFormDataContent();
            using var stream = file.OpenReadStream();
            content.Add(new StreamContent(stream), "file", file.FileName);

            try
            {
                var response = await client.PostAsync("http://127.0.0.1:5000/api/analyze", content);
                var responseString = await response.Content.ReadAsStringAsync();
                return StatusCode((int)response.StatusCode, responseString);
            }
            catch (Exception ex)
            {
                return StatusCode(503, new { error = "Python AI microservice is currently unreachable.", details = ex.Message });
            }
        }
    }
}
