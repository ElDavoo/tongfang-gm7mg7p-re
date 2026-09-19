using System;
using System.Text;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

public class TrayCtrl
{
	private string m_sRegPath = "\\OEM\\GamingCenter2";

	public static string m_icon_name = string.Empty;

	public static uint m_item_mode = 0u;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private uint m_nModeCount;

	private int m_ProjectID;

	public TrayCtrl()
	{
		m_nModeCount = GetFanModeCount();
		m_ProjectID = GetProjectIdFromEC();
	}

	public async void Recieve(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("TrayCtrl | Receive | msg = " + text);
		if (!(text == "GET"))
		{
			if (text == "SET")
			{
				string lang = val["Lang"];
				SetLang(lang);
			}
		}
		else
		{
			GetLang();
		}
	}

	public void ChangeIcon(uint mode, bool bIcon)
	{
	}

	private void GetLang()
	{
		string languageList = "en-us";
		string language = "en-us";
		try
		{
			languageList = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "LanguageList", "en-us");
			language = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
		}
		var data = new
		{
			LanguageList = languageList,
			Language = language
		};
		App.m_MQTTService.Publish("Languages/Info", data, retain: false);
		string oSDTpString = App.m_Osd.GetOSDTpString();
		App.m_MQTTService.Publish_ByUTF8("OSDTpDectect/Language", new
		{
			OSDTpString = oSDTpString
		}, retain: false);
	}

	private void SetLang(string sLang)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", sLang, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\TpDetect", "Language", sLang, RegistryValueKind.String);
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayCtrl | SetLang | RegistrySoftwareKeyWrite Failed {ex.ToString()}");
		}
		string oSDTpString = App.m_Osd.GetOSDTpString();
		App.m_MQTTService.Publish_ByUTF8("OSDTpDectect/Language", new
		{
			OSDTpString = oSDTpString
		}, retain: false);
	}

	private uint GetFanModeCount()
	{
		uint result = 2u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1183, ref Data);
		if (GetBitFromByte(Data, 1) == 1)
		{
			result = 3u;
		}
		if (RegistryCtrl.GetBridgeType() == 1)
		{
			result = 3u;
		}
		return result;
	}

	private int GetBitFromByte(byte data, int num)
	{
		return (data >> num) & 1;
	}

	private int GetProjectIdFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	public void LaunchAP()
	{
	}
}
