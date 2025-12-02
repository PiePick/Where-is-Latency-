using UnityEngine;
using System.Collections.Generic;
using System.IO;

public static class CSVLoader
{
    public static Dictionary<string, string> LoadCSVFromDataFolder(string fileName)
    {
        Dictionary<string, string> data = new Dictionary<string, string>();

        string path = Path.Combine(Application.dataPath, "data/" + fileName + ".csv");

        if (!File.Exists(path))
        {
            Debug.LogError("[CSVLoader] File not found: " + path);
            return data;
        }

        string[] lines = File.ReadAllLines(path);

        foreach (string line in lines)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            string[] parts = line.Trim().Split(',');
            if (parts.Length >= 2)
            {
                string key = parts[0].Trim();
                string value = parts[1].Trim();
                data[key] = value;
            }
        }

        return data;
    }
}
