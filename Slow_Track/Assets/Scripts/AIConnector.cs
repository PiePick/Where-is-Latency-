using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using System.Collections;
using System.Collections.Generic;

// 서버에서 받을 JSON 데이터 구조
[Serializable]
public class ServerPacket
{
    public string type;      // "fast" or "slow"
    public string emotion;   // 감정 라벨
    public string reaction;  // Fast Lane 반응
    public string keyword;   // 키워드 (옵션)
    public string latency;   // 처리 시간
    public string npc_reply; // Slow Lane 답변
}

public class AIConnector : MonoBehaviour
{
    [Header("Network Settings")]
    public string serverIP = "127.0.0.1";
    public int serverPort = 5000;

    private TcpClient client;
    private NetworkStream stream;
    private Thread receiveThread;
    private bool isRunning = false;

    // UI 표시용 변수
    private string logText = "";
    private string userInput = "";
    private Vector2 scrollPos;

    // 메인 쓰레드에서 UI 업데이트를 위한 큐
    private Queue<string> messageQueue = new Queue<string>();

    void Start()
    {
        ConnectToServer();
    }

    void ConnectToServer()
    {
        try
        {
            client = new TcpClient(serverIP, serverPort);
            stream = client.GetStream();
            isRunning = true;

            // 수신은 별도 쓰레드에서 계속 대기
            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            AddLog("서버에 접속되었습니다.");
        }
        catch (Exception e)
        {
            AddLog("서버 접속 실패. Python 서버를 먼저 켜주세요.\n" + e.Message);
        }
    }

    // 데이터 전송 함수
    public void SendData(string text)
    {
        if (client == null || !client.Connected) return;

        try
        {
            byte[] data = Encoding.UTF8.GetBytes(text);
            stream.Write(data, 0, data.Length);
            AddLog($"\n👤 User: {text}");
        }
        catch (Exception e)
        {
            AddLog("전송 에러: " + e.Message);
        }
    }

    // 데이터 수신 쓰레드 함수
    void ReceiveData()
    {
        byte[] buffer = new byte[4096];
        while (isRunning)
        {
            try
            {
                if (stream != null && stream.CanRead)
                {
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead > 0)
                    {
                        string jsonStr = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        // 패킷이 여러 개 붙어 올 수 있으므로 줄바꿈으로 분리
                        string[] packets = jsonStr.Split(new char[] { '\n' }, StringSplitOptions.RemoveEmptyEntries);
                        
                        foreach(string packet in packets)
                        {
                            // UI 업데이트는 메인 쓰레드에서 해야 하므로 큐에 넣음
                            lock (messageQueue)
                            {
                                messageQueue.Enqueue(packet);
                            }
                        }
                    }
                }
            }
            catch (Exception)
            {
                // 소켓 종료 등 예외 처리
                isRunning = false;
            }
        }
    }

    void Update()
    {
        // 큐에 쌓인 메시지를 메인 쓰레드에서 처리
        lock (messageQueue)
        {
            while (messageQueue.Count > 0)
            {
                string json = messageQueue.Dequeue();
                ProcessPacket(json);
            }
        }
    }

    // 수신된 JSON 처리 및 행동 지시
    void ProcessPacket(string json)
    {
        try
        {
            ServerPacket packet = JsonUtility.FromJson<ServerPacket>(json);

            if (packet.type == "fast")
            {
                AddLog($"[Fast] 감정: {packet.emotion} | 반응: \"{packet.reaction}\" ({packet.latency})");
                // TODO: 여기서 캐릭터 표정 변화 및 짧은 오디오 재생 함수 호출
            }
            else if (packet.type == "slow")
            {
                AddLog($"[Slow] NPC: \"{packet.npc_reply}\"");
                // TODO: 여기서 LLM 생성 문장 TTS 재생 및 입모양 싱크 호출
            }
        }
        catch (Exception e)
        {
            AddLog("패킷 파싱 에러: " + e.Message);
            Debug.LogWarning("JSON: " + json);
        }
    }

    void AddLog(string msg)
    {
        logText += msg + "\n";
        // 로그가 너무 길어지면 자르기
        if (logText.Length > 2000) logText = logText.Substring(logText.Length - 2000);
    }

    void OnApplicationQuit()
    {
        isRunning = false;
        if (stream != null) stream.Close();
        if (client != null) client.Close();
        if (receiveThread != null && receiveThread.IsAlive) receiveThread.Abort();
    }

    // GUI for Testing
    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(10, 10, 600, 800));
        
        GUILayout.Label("== AI NPC Chat Interface ==", GUI.skin.box);
        
        scrollPos = GUILayout.BeginScrollView(scrollPos, GUILayout.Height(600), GUILayout.Width(580));
        GUILayout.TextArea(logText, GUILayout.ExpandHeight(true));
        GUILayout.EndScrollView();

        GUILayout.Space(10);
        
        userInput = GUILayout.TextField(userInput, GUILayout.Height(30));

        if (GUILayout.Button("Send (Enter)", GUILayout.Height(40)) || (Event.current.isKey && Event.current.keyCode == KeyCode.Return))
        {
            if (!string.IsNullOrEmpty(userInput))
            {
                SendData(userInput);
                userInput = "";
            }
        }

        GUILayout.EndArea();
    }
}