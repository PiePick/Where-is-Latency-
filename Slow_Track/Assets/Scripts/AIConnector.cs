using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using TMPro;


// 서버 패킷 구조체
[Serializable]

public class ServerPacket
{
    public string type;      // fast or slow
    public string emotion;
    public string reaction;
    public string echo_text; // 에코잉 대사
    public string npc_reply; // LLM 대사
}

public class AIConnector : MonoBehaviour
{
    [Header("Connection")]
    public string serverIP = "127.0.0.1";
    public int serverPort = 5000;

    [Header("Chat UI")]
    public string userInput = "";
    
    // 대화 기록을 저장할 리스트 (로그 X, 채팅 O)
    private List<string> chatHistory = new List<string>();
    private Vector2 scrollPosition;

    private TcpClient client;
    private NetworkStream stream;
    private Thread receiveThread;
    private bool isRunning = false;
    
    // 메인 쓰레드 처리를 위한 큐
    private Queue<string> packetQueue = new Queue<string>();

    [SerializeField] private SpeechRecognizer speechRecognizer;

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

            AddToChat("[System] NPC와 연결되었습니다.");
        }
        catch (Exception)
        {
            AddToChat("[System] 서버 접속 실패. Python을 먼저 켜주세요.");
        }
    }

    public void SendData(string text)
    {
        if (client == null || !client.Connected) return;
        
        try 
        {
            byte[] data = Encoding.UTF8.GetBytes(text);
            stream.Write(data, 0, data.Length);
            
            // 보낸 내용 채팅창에 표시
            AddToChat($"User: {text}");
            text = "";
        }
        catch (Exception)
        {
            AddToChat("[System] 전송 실패");
        }
    }

    public void SendData()
    {
        if (client == null || !client.Connected) return;
        
        try 
        {
            byte[] data = Encoding.UTF8.GetBytes(userInput);
            stream.Write(data, 0, data.Length);
            
            // 보낸 내용 채팅창에 표시
            AddToChat($"User: {userInput}");
            userInput = "";
        }
        catch (Exception)
        {
            AddToChat("[System] 전송 실패");
        }
    }

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

        userInput = speechRecognizer.LastRecognitionResult;
    }

    // ★ 핵심 수정: 로그가 아니라 대화로 처리
    void ProcessPacket(string json)
    {
        try
        {
            ServerPacket packet = JsonUtility.FromJson<ServerPacket>(json);

            if (packet.type == "fast")
            {
                // [Fast Lane] 에코잉 + 리액션 합치기
                string finalLine = packet.reaction;

                // 에코잉이 있다면 앞에 붙여서 자연스럽게 만들기
                // 예: "Wallet?" + " " + "That sounds terrible."
                if (!string.IsNullOrEmpty(packet.echo_text))
                {
                    finalLine = $"{packet.echo_text} {packet.reaction}";
                }

                // NPC 대사로 출력 (로그 정보 제외)
                //AddToChat($"NPC: {finalLine}");

                ShowSubtitle(finalLine);

                StartCoroutine(PlayTTS(finalLine));
            }
            else if (packet.type == "slow")
            {
                // [Slow Lane] LLM 답변 출력
                //AddToChat($"NPC: {packet.npc_reply}");
                ShowSubtitle(packet.npc_reply);
                
                StartCoroutine(PlayTTS(packet.npc_reply));
            }
        }
        catch (Exception e)
        {
            Debug.LogError("Packet Error: " + e.Message);
        }
    }

    void AddToChat(string msg) 
    { 
        chatHistory.Add(msg);
        // 채팅이 너무 많아지면 오래된 것 삭제 (최근 20개만 유지)
        if (chatHistory.Count > 20)
        {
            chatHistory.RemoveAt(0);
        }
        // 스크롤 맨 아래로
        scrollPosition.y = float.MaxValue;
    }

    // 깔끔해진 채팅 UI
    // void OnGUI()
    // {
    //     // 폰트 크기 키움
    //     GUI.skin.label.fontSize = 24;
    //     GUI.skin.textField.fontSize = 24;
    //     GUI.skin.button.fontSize = 24;
    //     GUI.skin.box.fontSize = 24;

    //     float padding = 20f;
    //     GUILayout.BeginArea(new Rect(padding, padding, Screen.width - padding*2, Screen.height - padding*2));
        
    //     GUILayout.Label("== Chat with AI NPC ==", GUI.skin.box, GUILayout.Height(50));
        
    //     scrollPosition = GUILayout.BeginScrollView(scrollPosition, GUILayout.ExpandHeight(true));
        
    //     foreach (string msg in chatHistory)
    //     {
    //         // 말한 사람에 따라 색상이나 스타일을 다르게 줄 수도 있음
    //         if (msg.StartsWith("User:")) GUI.color = Color.yellow;
    //         else if (msg.StartsWith("NPC:")) GUI.color = Color.white;
    //         else GUI.color = Color.gray; // 시스템 메시지

    //         GUILayout.Label(msg);
    //     }
    //     GUI.color = Color.white; // 색상 복구

    //     GUILayout.EndScrollView();

    //     GUILayout.Space(10);
        
    //     GUILayout.EndArea();
    // }

    [SerializeField] private TextMeshProUGUI subtitleText;


    void ShowSubtitle(string line)
    {
        subtitleText.text = line;
        subtitleText.gameObject.SetActive(true);
    }

    IEnumerator PlayTTS(string line)
    {
        yield return null;
        WinTTS.Speak(line);
    }

    //아래는 자막유지시간 적용시
    // private Coroutine subtitleCoroutine;

    // void ShowSubtitle(string line)
    // {
    //     if (subtitleCoroutine != null)
    //         StopCoroutine(subtitleCoroutine);

    //     subtitleCoroutine = StartCoroutine(SubtitleRoutine(line));
    // }

    // IEnumerator SubtitleRoutine(string line)
    // {
    //     subtitleText.text = line;
    //     subtitleText.gameObject.SetActive(true);

    //     yield return new WaitForSeconds(4f); // 자막 유지 시간

    //     subtitleText.gameObject.SetActive(false);
    // }

    // void OnApplicationQuit()
    // {
    //     isRunning = false;
    //     if(client != null) client.Close();
    //     if(receiveThread != null) receiveThread.Abort();
    // }
}