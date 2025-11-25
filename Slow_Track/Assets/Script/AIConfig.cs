using UnityEngine;
using System.Collections.Generic;

public class AIConfig : MonoBehaviour
{
    public static string GeminiKey;

    void Awake()
    {
        Dictionary<string, string> config = CSVLoader.LoadCSVFromDataFolder("private_data");

        if (config.TryGetValue("gemini_api_key", out string key))
            GeminiKey = key;

        Debug.Log("=== AIConfig Loaded ===");
        Debug.Log("Gemini Key Loaded: " + (string.IsNullOrEmpty(GeminiKey) ? "NO" : "YES"));
    }
}
