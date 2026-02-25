#define UNICODE
#define _UNICODE

#include <windows.h>
#include <sapi.h>

static ISpVoice* g_pVoice = NULL;
static bool g_isInitialized = false;

extern "C"
{
    // =========================================
    // TTS 초기화 (Unity 시작 시 1번 호출)
    // =========================================
    __declspec(dllexport) void InitTTS()
    {
        if (g_isInitialized)
            return;

        HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        if (FAILED(hr))
            return;

        hr = CoCreateInstance(
            CLSID_SpVoice,
            NULL,
            CLSCTX_ALL,
            IID_ISpVoice,
            (void**)&g_pVoice
        );

        if (FAILED(hr))
        {
            CoUninitialize();
            return;
        }

        // ===============================
        // 영어(en-US) 보이스 선택
        // ===============================
        ISpObjectTokenCategory* pCategory = NULL;
        IEnumSpObjectTokens* pEnum = NULL;
        ISpObjectToken* pToken = NULL;

        hr = CoCreateInstance(
            CLSID_SpObjectTokenCategory,
            NULL,
            CLSCTX_ALL,
            IID_ISpObjectTokenCategory,
            (void**)&pCategory
        );

        if (SUCCEEDED(hr))
        {
            hr = pCategory->SetId(SPCAT_VOICES, FALSE);
            if (SUCCEEDED(hr))
            {
                hr = pCategory->EnumTokens(L"Language=409", NULL, &pEnum);
                if (SUCCEEDED(hr))
                {
                    ULONG fetched = 0;
                    if (SUCCEEDED(pEnum->Next(1, &pToken, &fetched)) && fetched > 0)
                    {
                        g_pVoice->SetVoice(pToken);
                        pToken->Release();
                    }
                    pEnum->Release();
                }
            }
            pCategory->Release();
        }

        g_isInitialized = true;
    }

    // =========================================
    // 말하기 (비동기)
    // =========================================
    __declspec(dllexport) void SpeakText(const wchar_t* text)
    {
        if (!g_isInitialized || !g_pVoice)
            return;

        // 이전 음성 중단
        g_pVoice->Speak(NULL, SPF_PURGEBEFORESPEAK, NULL);

        // 비동기 재생
        g_pVoice->Speak(text, SPF_ASYNC, NULL);
    }

    // =========================================
    // 종료 처리 (Unity 종료 시 1번 호출)
    // =========================================
    __declspec(dllexport) void ShutdownTTS()
    {
        if (g_pVoice)
        {
            g_pVoice->Release();
            g_pVoice = NULL;
        }

        if (g_isInitialized)
        {
            CoUninitialize();
            g_isInitialized = false;
        }
    }
}