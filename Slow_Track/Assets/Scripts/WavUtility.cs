using System;
using System.IO;
using UnityEngine;

public static class WavUtility
{
    public static byte[] AudioClipToWav(AudioClip clip)
    {
        var samples = new float[clip.samples];
        clip.GetData(samples, 0);

        MemoryStream stream = new MemoryStream();

        int sampleRate = clip.frequency;
        int channels = clip.channels;
        int byteRate = sampleRate * channels * 2;

        stream.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"), 0, 4);
        stream.Write(BitConverter.GetBytes(36 + samples.Length * 2), 0, 4);
        stream.Write(System.Text.Encoding.ASCII.GetBytes("WAVE"), 0, 4);
        stream.Write(System.Text.Encoding.ASCII.GetBytes("fmt "), 0, 4);
        stream.Write(BitConverter.GetBytes(16), 0, 4);
        stream.Write(BitConverter.GetBytes((ushort)1), 0, 2);
        stream.Write(BitConverter.GetBytes((ushort)channels), 0, 2);
        stream.Write(BitConverter.GetBytes(sampleRate), 0, 4);
        stream.Write(BitConverter.GetBytes(byteRate), 0, 4);
        stream.Write(BitConverter.GetBytes((ushort)(channels * 2)), 0, 2);
        stream.Write(BitConverter.GetBytes((ushort)16), 0, 2);

        stream.Write(System.Text.Encoding.ASCII.GetBytes("data"), 0, 4);
        stream.Write(BitConverter.GetBytes(samples.Length * 2), 0, 4);

        foreach (var s in samples)
        {
            short val = (short)(s * short.MaxValue);
            stream.Write(BitConverter.GetBytes(val), 0, 2);
        }

        return stream.ToArray();
    }
}
