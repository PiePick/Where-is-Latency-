#define UNICODE
#define _UNICODE

#include <windows.h>
#include <sapi.h>

extern "C"
{
    __declspec(dllexport) void SpeakText(const wchar_t* text)
    {
        HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        if (FAILED(hr))
            return;

        ISpVoice* pVoice = NULL;
        hr = CoCreateInstance(
            CLSID_SpVoice,
            NULL,
            CLSCTX_ALL,
            IID_ISpVoice,
            (void**)&pVoice
        );

        if (FAILED(hr))
        {
            CoUninitialize();
            return;
        }

        // ===============================
        // 영어(en-US) 보이스 직접 선택
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
                        pVoice->SetVoice(pToken);
                        pToken->Release();
                    }
                    pEnum->Release();
                }
            }
            pCategory->Release();
        }
        // ===============================

        hr = pVoice->Speak(text, SPF_DEFAULT, NULL);
        if (SUCCEEDED(hr))
        {
            pVoice->WaitUntilDone(INFINITE);
        }

        pVoice->Release();
        CoUninitialize();
    }
}
