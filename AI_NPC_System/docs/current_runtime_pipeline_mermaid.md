# Current CREDO Runtime Pipeline Mermaid

작성 기준: 2026-05-29 KST

이 그림은 논문 초고의 현재 1차 실험 기준만 표현한다. 보류/비활성 항목인
Unity, TCP stream, ASR/STT, YouTube live mode, spaCy spoken echo,
Parallel/prefetch scheduling, standalone nonverbal interjection audio는 포함하지
않는다.

## Paper Figure Version

```mermaid
flowchart LR
  subgraph INPUT["Input"]
    A1["Virtual broadcast chat"]
    A2["Donation message"]
    A3["1:1 text input"]
    A4["Idle trigger"]
  end

  subgraph FRONTEND["Open-LLM-VTuber Browser UI"]
    B1["CREDO VTuber Mode panel"]
    B2["WebSocket text input"]
    B3["HTTP donation route"]
    B4["Donation overlay + SFX + readout gate"]
  end

  subgraph AGENT["CREDO Latency-Cover Agent"]
    C1["Turn router<br/>donation priority<br/>recent chat buffer<br/>experiment condition"]
    C2["FastTrack analysis<br/>GoEmotions emotion label<br/>SWDA incoming intent<br/>SWDA response-act transition"]
    C3["Contextual mapping<br/>Grounded<br/>Emotion Only<br/>Intent Only<br/>Neutral Random"]
    C4["Prebuilt FastTrack audio lookup<br/>StyleBERT-VITS2 wav index<br/>GoEmotions/SWDA provenance preserved"]
    C5["SlowTrack generation<br/>persona + memory + broadcast direction<br/>local LLM response<br/>realtime StyleBERT-VITS2 TTS"]
    C6["Serial output scheduler<br/>FastTrack first when enabled<br/>SlowTrack main response afterward"]
  end

  subgraph OUTPUT["VTuber Output"]
    D1["Speech subtitles"]
    D2["Audio playback"]
    D3["Live2D lip-sync"]
    D4["Expression + body + idle motion"]
  end

  subgraph LOG["Latency Logging"]
    E1["module_events.csv<br/>experiment_run_id<br/>selection_policy<br/>component_mode<br/>scheduling_mode<br/>fasttrack_analysis<br/>fasttrack_audio<br/>slowtrack_llm<br/>slowtrack_tts<br/>turn_total"]
  end

  A1 --> B2
  A2 --> B3
  A3 --> B2
  A4 --> B2
  B1 --> C1
  B2 --> C1
  B3 --> B4 --> C1

  C1 --> C2 --> C3 --> C4 --> C6
  C1 --> C5 --> C6
  C6 --> D1
  C6 --> D2
  C6 --> D3
  C6 --> D4
  C2 --> E1
  C4 --> E1
  C5 --> E1
  C6 --> E1
```

## Offline FastTrack Audio Build

```mermaid
flowchart LR
  A["Filtered GoEmotions evidence pool"] --> C["Persona-safe cover composition"]
  B["Filtered SWDA response-act evidence pool<br/>QUESTION excluded from output acts"] --> C
  C --> D["Short FastTrack text"]
  D --> E["Quality filtering<br/>no greetings, fillers, profanity,<br/>hidden context, or niche references"]
  E --> F["StyleBERT-VITS2 prebuild"]
  F --> G["Audio index<br/>wav path + text + source provenance"]
  G --> H["Runtime FastTrack lookup"]
```
