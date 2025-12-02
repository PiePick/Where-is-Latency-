using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using System.Collections;
using System.Collections.Generic;

// 서버 패킷 구조체
[Serializable]
public class ServerPacket
{
    public string type;      // fast or slow
    public string emotion;   // 감정 (Fast)
    public string reaction;  // 리액션 대사 (Fast)
    public string keyword;   // 키워드 (Fast)
    public string npc_reply; // LLM 답변 (Slow)
    public string latency;   // 처리 시간
}

public class AIConnector : MonoBehaviour
{
    [Header("Connection")]
    public string serverIP = "127.0.0.1";
    public int serverPort = 5000;

    [Header("Debug UI")]
    [TextArea] public string logText = "";
    public string userInput = "";

    private TcpClient client;
    private NetworkStream stream;
    private Thread receiveThread;
    private bool isRunning = false;
    private Queue<string> packetQueue = new Queue<string>();

    // 화면 스크롤 위치
    private Vector2 scrollPosition;

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

            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            AddLog("[System] Connected to Server.");
        }
        catch (Exception e)
        {
            AddLog("[Error] Connection Failed: " + e.Message);
        }
    }

    // 1. 데이터 전송 (Input -> Python)
    public void SendData(string text)
    {
        if (client == null || !client.Connected) return;
        
        try 
        {
            byte[] data = Encoding.UTF8.GetBytes(text);
            stream.Write(data, 0, data.Length);
            AddLog($"\n[User] {text}");
        }
        catch (Exception e)
        {
            AddLog("[Error] Send Failed: " + e.Message);
        }
    }

    // 2. 데이터 수신 (Python -> Output Queue)
    void ReceiveData()
    {
        byte[] buffer = new byte[8192];
        while (isRunning)
        {
            try
            {
                if (stream != null && stream.CanRead)
                {
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead > 0)
                    {
                        string raw = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        string[] packets = raw.Split(new char[] { '\n' }, StringSplitOptions.RemoveEmptyEntries);
                        
                        foreach(string p in packets)
                        {
                            lock(packetQueue)
                            {
                                packetQueue.Enqueue(p);
                            }
                        }
                    }
                }
            }
            catch (Exception) { isRunning = false; }
        }
    }

    // 3. 메인 쓰레드 처리 (Queue -> Action)
    void Update()
    {
        lock(packetQueue)
        {
            while (packetQueue.Count > 0)
            {
                string json = packetQueue.Dequeue();
                ProcessPacket(json);
            }
        }
    }

    void ProcessPacket(string json)
    {
        try
        {
            ServerPacket packet = JsonUtility.FromJson<ServerPacket>(json);

            if (packet.type == "fast")
            {
                // Fast Track 결과
                AddLog($"[Fast Track] Emotion: {packet.emotion} | Reaction: \"{packet.reaction}\"");
            }
            else if (packet.type == "slow")
            {
                // Slow Track 결과
                AddLog($"[Slow Track] NPC: \"{packet.npc_reply}\"");
            }
        }
        catch (Exception e)
        {
            Debug.LogError("JSON Parse Error: " + e.Message);
        }
    }

    void AddLog(string msg) 
    { 
        logText += msg + "\n";
        // 로그가 너무 길어지면 자름
        if (logText.Length > 5000)
        {
            logText = logText.Substring(logText.Length - 5000);
        }
        // 로그 추가 시 스크롤을 맨 아래로 이동
        scrollPosition.y = float.MaxValue;
    }

    void OnGUI()
    {
        // UI 스타일 크기 설정 (가독성을 위해 크게 변경)
        GUI.skin.label.fontSize = 28;
        GUI.skin.button.fontSize = 28;
        GUI.skin.textArea.fontSize = 28;
        GUI.skin.textField.fontSize = 28;
        GUI.skin.box.fontSize = 30;

        float padding = 40f;
        float areaWidth = Screen.width - (padding * 2);
        float areaHeight = Screen.height - (padding * 2);

        // 화면 전체 영역 잡기
        GUILayout.BeginArea(new Rect(padding, padding, areaWidth, areaHeight));
        
        GUILayout.Label("== Dual Pipeline Test Interface ==", GUI.skin.box, GUILayout.Height(60));
        
        // 로그 출력 영역 (스크롤뷰 적용)
        scrollPosition = GUILayout.BeginScrollView(scrollPosition, GUILayout.ExpandHeight(true));
        GUILayout.TextArea(logText);
        GUILayout.EndScrollView();

        GUILayout.Space(20);
        
        // 입력창 및 전송 버튼
        userInput = GUILayout.TextField(userInput, GUILayout.Height(60)); // 높이 60으로 확대
        
        GUILayout.Space(10);

        if (GUILayout.Button("Send Message (Enter)", GUILayout.Height(80)) || // 높이 80으로 확대
           (Event.current.isKey && Event.current.keyCode == KeyCode.Return && Event.current.type == EventType.KeyUp))
        {
            if (!string.IsNullOrEmpty(userInput))
            {
                SendData(userInput);
                userInput = "";
                // 입력 후 포커스 유지 (편의성)
                GUI.FocusControl(""); 
            }
        }

        GUILayout.EndArea();
    }

    void OnApplicationQuit()
    {
        isRunning = false;
        if(client != null) client.Close();
        if(receiveThread != null) receiveThread.Abort();
    }
}