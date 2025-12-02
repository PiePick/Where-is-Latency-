using UnityEngine;
using System.Collections.Generic;

public class AIConfig : MonoBehaviour
{
    public static string GPTApiKey;
    public static string GeminiApiKey;

    public static string GPTModel;
    public static string GeminiModel;

    void Awake()
    {
        Dictionary<string, string> config =
            CSVLoader.LoadCSVFromDataFolder("private_data");

        // GPT용 API / 모델
        config.TryGetValue("gpt_api_key", out GPTApiKey);
        config.TryGetValue("gpt_model", out GPTModel);

        // Gemini용 API / 모델
        config.TryGetValue("gemini_api_key", out GeminiApiKey);
        config.TryGetValue("gemini_model", out GeminiModel);

        Debug.Log("=== AIConfig Loaded ===");
        Debug.Log("[GPT Key]     " + (string.IsNullOrEmpty(GPTApiKey) ? "NULL" : "LOADED"));
        Debug.Log("[Gemini Key]  " + (string.IsNullOrEmpty(GeminiApiKey) ? "NULL" : "LOADED"));
        Debug.Log("[GPT Model]   " + GPTModel);
        Debug.Log("[GeminiModel] " + GeminiModel);
    }
}
