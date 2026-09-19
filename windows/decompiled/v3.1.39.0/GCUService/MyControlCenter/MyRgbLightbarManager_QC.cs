using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class MyRgbLightbarManager_QC : MyRgbLightbarManager
{
	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyRgbLightbarView m_View = new MyRgbLightbarView();

	private string m_path = "\\OEM\\GamingCenter2\\MyLightBar";

	private uint m_LightBarOnOff = 1u;

	private uint m_red_level = 9u;

	private uint m_green_level = 9u;

	private uint m_blue_level = 9u;

	private uint m_red_level_dc;

	private uint m_green_level_dc;

	private uint m_blue_level_dc;

	private uint m_Colorful;

	private uint m_Colorful_dc;

	private uint m_BreathingLightEffect = 1u;

	private uint m_SupportRGBLightBarColorful = 1u;

	private uint m_SupportRGBLightBarBreathEffect = 1u;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private KeyboardCloseTimer keyboardcloseTimer = KeyboardCloseTimer.CreateInstance;

	public override void Enable()
	{
		LoadRegistry();
		SetApExist(1);
		SetMyLightBarOnOff(m_LightBarOnOff);
		_ = m_LightBarOnOff;
		ValueChanged(PowerModeEvent.g_ACLineStatus);
		SetBreathingMordenStandby(0u);
		keyboardcloseTimer.ControlBrigtnessEvent += KeyboardcloseTimer_ControlPowerEvent;
	}

	public override void Disable()
	{
		SetApExist(0);
	}

	public override async void Recieve(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(className + "[Recieve] msg = " + text);
		switch (text)
		{
		case "GETSTATUS":
			UpdateStatusToClient(1);
			break;
		case "DEFAULT":
			UserSetDefault();
			UpdateStatusToClient(1);
			break;
		case "POWER_ON":
			UserSetPower(1u);
			UpdateStatusToClient(1);
			break;
		case "POWER_OFF":
			UserSetPower(0u);
			UpdateStatusToClient(1);
			break;
		case "RL":
		{
			string s = val["Level"];
			UserSetBarLevel("RL", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "GL":
		{
			string s = val["Level"];
			UserSetBarLevel("GL", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "BL":
		{
			string s = val["Level"];
			UserSetBarLevel("BL", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "RL_DC":
		{
			string s = val["Level"];
			UserSetBarLevel("RL_DC", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "GL_DC":
		{
			string s = val["Level"];
			UserSetBarLevel("GL_DC", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "BL_DC":
		{
			string s = val["Level"];
			UserSetBarLevel("BL_DC", uint.Parse(s));
			UpdateStatusToClient(1);
			break;
		}
		case "COLORFUL_ON":
		case "COLORFUL_OFF":
			UserSetColorful(text, val);
			UpdateStatusToClient(1);
			break;
		case "BREATHINGLIGHT_ON":
		case "BREATHINGLIGHT_OFF":
			UserSetBreathingLight(text);
			UpdateStatusToClient(1);
			break;
		case "COPY_AC_SETTINGS":
			UserCopyAcSettings();
			UpdateStatusToClient(1);
			break;
		}
	}

	public override void UpdateStatusToClient(int run)
	{
		if (run != 0)
		{
			var data = new
			{
				POWER = m_LightBarOnOff.ToString(),
				RL = m_red_level.ToString(),
				GL = m_green_level.ToString(),
				BL = m_blue_level.ToString(),
				RL_DC = m_red_level_dc.ToString(),
				GL_DC = m_green_level_dc.ToString(),
				BL_DC = m_blue_level_dc.ToString(),
				COLORFUL = m_Colorful.ToString(),
				COLORFUL_DC = m_Colorful_dc.ToString(),
				BREATHINGLIGHT = m_BreathingLightEffect.ToString(),
				ACLINESTATUS = PowerModeEvent.g_ACLineStatus.ToString()
			};
			m_View.SendStatusToClient(data);
		}
	}

	public override void Resume()
	{
		SetApExist(1);
		LoadRegistry();
		SetMyLightBarOnOff(m_LightBarOnOff);
		_ = m_LightBarOnOff;
		ValueChanged(PowerModeEvent.g_ACLineStatus);
		if (m_SupportRGBLightBarBreathEffect == 1 && m_BreathingLightEffect == 1)
		{
			SetBreathingMordenStandby(0u);
		}
	}

	public override void OnModernStandby()
	{
		if (m_SupportRGBLightBarBreathEffect == 1)
		{
			SetRedLevel(0u, bWriteToECRam: true);
			SetGreenLevel(0u, bWriteToECRam: true);
			SetBlueLevel(0u, bWriteToECRam: true);
			if (m_BreathingLightEffect == 1)
			{
				SetBreathingMordenStandby(1u);
			}
		}
	}

	public override void PowerStatusChange(int mode)
	{
		LoadRegistryForLineStatus();
		ValueChanged(mode);
	}

	public override void Suspend()
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(className + "[Suspend]");
	}

	public override void Uninstall()
	{
		string subKey = "\\OEM\\GamingCenter2";
		try
		{
			if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1) != -1)
			{
				RegistryCtrl.RegistrySoftwareSubKeyTreeDelete(RegistryHive.LocalMachine, subKey, "MyLightBar");
			}
			LogCtrl.Write(className + "[Uninstall] Delete Registry OK!");
		}
		catch
		{
			LogCtrl.Write(className + "[Uninstall] No Registry!");
		}
	}

	public override void Default()
	{
		string parentDirectoryPath = LogCtrl.GetParentDirectoryPath(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName, 2);
		string arguments = "/s \"" + parentDirectoryPath + "\\MyLightBar.reg\"";
		Process.Start("regedit.exe", arguments).WaitForExit();
		LoadRegistry();
		SetMyLightBarOnOff(m_LightBarOnOff);
		_ = m_LightBarOnOff;
		ValueChanged(PowerModeEvent.g_ACLineStatus);
		SetBreathingMordenStandby(0u);
		LogCtrl.Write(className + "[Default] End");
	}

	private void Save()
	{
		if (m_SupportRGBLightBarColorful == 1)
		{
			SetRegistry("Colorful", m_Colorful);
			SetRegistry("Colorful_dc", m_Colorful_dc);
		}
		if (m_SupportRGBLightBarBreathEffect == 1)
		{
			SetRegistry("BreathingLightEffect", m_BreathingLightEffect);
		}
		SetRegistry("RedLevel", m_red_level);
		SetRegistry("GreenLevel", m_green_level);
		SetRegistry("BlueLevel", m_blue_level);
		SetRegistry("RedLevel_dc", m_red_level_dc);
		SetRegistry("GreenLevel_dc", m_green_level_dc);
		SetRegistry("BlueLevel_dc", m_blue_level_dc);
		SetRegistry("LightBarOnOff", m_LightBarOnOff);
		LogCtrl.Write(className + "[Save] End");
	}

	private void UserSetDefault()
	{
		Default();
	}

	private void UserSetPower(uint status)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		m_LightBarOnOff = status;
		SetMyLightBarOnOff(status);
		_ = m_LightBarOnOff;
		SetRegistry("LightBarOnOff", status);
	}

	private void UserSetColorful(string action, dynamic data)
	{
		if (m_SupportRGBLightBarColorful == 0 || !((data["Page"] != null) ? true : false))
		{
			return;
		}
		if (Convert.ToString(data["Page"]) == "AC")
		{
			if (!(action == "COLORFUL_ON"))
			{
				if (action == "COLORFUL_OFF")
				{
					m_Colorful = 0u;
				}
			}
			else
			{
				m_Colorful = 1u;
			}
			SetRegistry("Colorful", m_Colorful);
			if (PowerModeEvent.g_ACLineStatus == 1)
			{
				ValueChanged(PowerModeEvent.g_ACLineStatus);
			}
			return;
		}
		if (!(action == "COLORFUL_ON"))
		{
			if (action == "COLORFUL_OFF")
			{
				m_Colorful_dc = 0u;
			}
		}
		else
		{
			m_Colorful_dc = 1u;
		}
		SetRegistry("Colorful_dc", m_Colorful_dc);
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			ValueChanged(PowerModeEvent.g_ACLineStatus);
		}
	}

	private void UserSetBreathingLight(string action)
	{
		if (m_SupportRGBLightBarBreathEffect == 0)
		{
			return;
		}
		if (!(action == "BREATHINGLIGHT_ON"))
		{
			if (action == "BREATHINGLIGHT_OFF")
			{
				m_BreathingLightEffect = 0u;
			}
		}
		else
		{
			m_BreathingLightEffect = 1u;
		}
		if (m_LightBarOnOff == 1)
		{
			SetBreathingLightEffect(m_BreathingLightEffect);
		}
		SetRegistry("BreathingLightEffect", m_BreathingLightEffect);
	}

	private void UserCopyAcSettings()
	{
		m_Colorful_dc = m_Colorful;
		m_red_level_dc = m_red_level;
		m_green_level_dc = m_green_level;
		m_blue_level_dc = m_blue_level;
		SetRegistry("Colorful_dc", m_Colorful_dc);
		SetRegistry("RedLevel_dc", m_red_level_dc);
		SetRegistry("GreenLevel_dc", m_green_level_dc);
		SetRegistry("BlueLevel_dc", m_blue_level_dc);
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			ValueChanged(PowerModeEvent.g_ACLineStatus);
		}
	}

	private void UserSetBarLevel(string key, uint level)
	{
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			switch (key)
			{
			case "RL":
				m_red_level = level;
				SetRegistry("RedLevel", m_red_level);
				break;
			case "GL":
				m_green_level = level;
				SetRegistry("GreenLevel", m_green_level);
				break;
			case "BL":
				m_blue_level = level;
				SetRegistry("BlueLevel", m_blue_level);
				break;
			case "RL_DC":
				m_red_level_dc = level;
				SetRedLevel(level, bWriteToECRam: true);
				SetRegistry("RedLevel_dc", m_red_level_dc);
				break;
			case "GL_DC":
				m_green_level_dc = level;
				SetGreenLevel(level, bWriteToECRam: true);
				SetRegistry("GreenLevel_dc", m_green_level_dc);
				break;
			case "BL_DC":
				m_blue_level_dc = level;
				SetBlueLevel(level, bWriteToECRam: true);
				SetRegistry("BlueLevel_dc", m_blue_level_dc);
				break;
			}
		}
		else
		{
			switch (key)
			{
			case "RL":
				m_red_level = level;
				SetRedLevel(level, bWriteToECRam: true);
				SetRegistry("RedLevel", m_red_level);
				break;
			case "GL":
				m_green_level = level;
				SetGreenLevel(level, bWriteToECRam: true);
				SetRegistry("GreenLevel", m_green_level);
				break;
			case "BL":
				m_blue_level = level;
				SetBlueLevel(level, bWriteToECRam: true);
				SetRegistry("BlueLevel", m_blue_level);
				break;
			case "RL_DC":
				m_red_level_dc = level;
				SetRegistry("RedLevel_dc", m_red_level_dc);
				break;
			case "GL_DC":
				m_green_level_dc = level;
				SetRegistry("GreenLevel_dc", m_green_level_dc);
				break;
			case "BL_DC":
				m_blue_level_dc = level;
				SetRegistry("BlueLevel_dc", m_blue_level_dc);
				break;
			}
		}
	}

	private void ValueChanged(int mode)
	{
		switch (mode)
		{
		case 0:
			LogCtrl.Write(className + "[ValueChanged] OffLine");
			if (m_Colorful_dc == 0)
			{
				SetRedLevel(m_red_level_dc, bWriteToECRam: true);
				SetGreenLevel(m_green_level_dc, bWriteToECRam: true);
				SetBlueLevel(m_blue_level_dc, bWriteToECRam: true);
			}
			else
			{
				SetRedLevel(0u, bWriteToECRam: true);
				SetGreenLevel(0u, bWriteToECRam: true);
				SetBlueLevel(0u, bWriteToECRam: true);
			}
			SetColorful(m_Colorful_dc);
			break;
		case 1:
			LogCtrl.Write(className + "[ValueChanged] OnLine");
			if (m_Colorful == 0)
			{
				SetRedLevel(m_red_level, bWriteToECRam: true);
				SetGreenLevel(m_green_level, bWriteToECRam: true);
				SetBlueLevel(m_blue_level, bWriteToECRam: true);
			}
			else
			{
				SetRedLevel(0u, bWriteToECRam: true);
				SetGreenLevel(0u, bWriteToECRam: true);
				SetBlueLevel(0u, bWriteToECRam: true);
			}
			SetColorful(m_Colorful);
			break;
		}
	}

	private void SetColorful(uint mode)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1864, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if (mode == 1)
		{
			byte data = (byte)(b | 0x80);
			EcCtrl.Write(GetType().Name, 1864, data);
			LogCtrl.Write(className + "[SetColorful] 0x0748.7 = 1 WelcomeMode ON");
		}
		else
		{
			byte data2 = (byte)(b & 0x7F);
			EcCtrl.Write(GetType().Name, 1864, data2);
			LogCtrl.Write(className + "[SetColorful] 0x0748.7 = 0 WelcomeMode OFF");
		}
	}

	private void SetBreathingLightEffect(uint mode)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1864, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if (mode == 0)
		{
			byte data = (byte)(b | 8);
			EcCtrl.Write(GetType().Name, 1864, data);
		}
		else
		{
			byte data2 = (byte)(b & 0xF7);
			EcCtrl.Write(GetType().Name, 1864, data2);
		}
	}

	private void SetBreathingMordenStandby(uint mode)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1864, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if (mode == 1)
		{
			byte data = (byte)(b | 0x40);
			EcCtrl.Write(GetType().Name, 1864, data);
			LogCtrl.Write(className + "[SetBreathingMordenStandby] 0x0748.6 = 1 Breathing ON");
		}
		else
		{
			byte data2 = (byte)(b & 0xBF);
			EcCtrl.Write(GetType().Name, 1864, data2);
			LogCtrl.Write(className + "[SetBreathingMordenStandby] 0x0748.6 = 0 Breathing OFF");
		}
	}

	private void SetMyLightBarOnOff(uint mode)
	{
		try
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1864, ref Data);
			byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
			switch (mode)
			{
			case 1u:
				b &= 0xFB;
				break;
			case 0u:
				b |= 4;
				break;
			}
			EcCtrl.Write(GetType().Name, 1864, b);
		}
		catch
		{
			LogCtrl.Write(className + "[SetMyLightBarOnOff] fail.");
		}
	}

	private void SetApExist(int mode)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1864, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		b = ((mode != 0) ? ((byte)(b | 1)) : ((byte)(b & 0xFE)));
		EcCtrl.Write(GetType().Name, 1864, b);
		LogCtrl.Write(string.Format(className + "[SetApExist] After SetApExist, AP read 0x0748h = 0x{0:X}", b));
	}

	private void SetRedLevel(uint level, bool bWriteToECRam)
	{
		ulong num = 0uL;
		num = RGBLightBarTable_QC.GetTable("Red", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format(className + "[SetRedLevel] RedLevel = {0}, 0x0749h = {0}", level, level));
			EcCtrl.Write(GetType().Name, 1865, (byte)num);
		}
	}

	private void SetGreenLevel(uint level, bool bWriteToECRam)
	{
		ulong num = 0uL;
		num = RGBLightBarTable_QC.GetTable("Green", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format(className + "[SetGreenLevel] GreenLevel = {0}, 0x074Ah = {0}", level, level));
			EcCtrl.Write(GetType().Name, 1866, (byte)num);
		}
	}

	private void SetBlueLevel(uint level, bool bWriteToECRam)
	{
		ulong num = 0uL;
		num = RGBLightBarTable_QC.GetTable("Blue", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format(className + "[SetBlueLevel] BlueLevel = {0}, 0x074Bh = {0}", level, level));
			EcCtrl.Write(GetType().Name, 1867, (byte)num);
		}
	}

	private void SetTriggerBit4()
	{
		try
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1864, ref Data);
			byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
			LogCtrl.Write(string.Format(className + "[SetTriggerBit4] Before SetTriggerBit4, AP read 0x0748h = 0x{0:X}", b));
			b |= 0x10;
			EcCtrl.Write(GetType().Name, 1864, b);
			LogCtrl.Write(string.Format(className + "[SetTriggerBit4] After SetTriggerBit4, AP read 0x0748h = 0x{0:X}", b));
		}
		catch
		{
			Console.WriteLine(className + "[SetTriggerBit4] failed.");
		}
	}

	private void SetTriggerBit5()
	{
		try
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1864, ref Data);
			byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
			LogCtrl.Write(string.Format(className + "[SetTriggerBit5] Before SetTriggerBit5, AP read 0x0748h = 0x{0:X}", b));
			b |= 0x20;
			EcCtrl.Write(GetType().Name, 1864, b);
			LogCtrl.Write(string.Format(className + "[SetTriggerBit5] After SetTriggerBit5, AP read 0x0748h = 0x{0:X}", b));
		}
		catch
		{
			Console.WriteLine(className + "[SetTriggerBit5] failed.");
		}
	}

	private void LoadRegistry()
	{
		try
		{
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel", 9u);
			int num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel", 9u);
			int num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel", 9u);
			int num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel_dc", 0u);
			int num5 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel_dc", 0u);
			int num6 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel_dc", 0u);
			int num7 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful", 0);
			int num8 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful_dc", 0);
			int num9 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BreathingLightEffect", 1);
			int num10 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", 1);
			int num11 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", 1);
			int num12 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1);
			if ((long)num < 0L || (long)num > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "RedLevel", 9u, RegistryValueKind.DWord);
				num = 9;
			}
			if ((long)num2 < 0L || (long)num2 > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "GreenLevel", 9u, RegistryValueKind.DWord);
				num2 = 9;
			}
			if ((long)num3 < 0L || (long)num3 > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BlueLevel", 9u, RegistryValueKind.DWord);
				num3 = 9;
			}
			if ((long)num4 < 0L || (long)num4 > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "RedLevel_dc", 0u, RegistryValueKind.DWord);
				num4 = 0;
			}
			if ((long)num5 < 0L || (long)num5 > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "GreenLevel_dc", 0u, RegistryValueKind.DWord);
				num5 = 0;
			}
			if ((long)num6 < 0L || (long)num6 > 9L)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BlueLevel_dc", 0u, RegistryValueKind.DWord);
				num6 = 0;
			}
			if (num7 < -1 || num7 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "Colorful", 0, RegistryValueKind.DWord);
				num7 = 0;
			}
			if (num8 < -1 || num8 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "Colorful_dc", 0, RegistryValueKind.DWord);
				num8 = 0;
			}
			if (num9 < -1 || num9 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BreathingLightEffect", 1, RegistryValueKind.DWord);
				num9 = 1;
			}
			if (num10 < 0 || num10 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", 1, RegistryValueKind.DWord);
				num10 = 1;
			}
			if (num11 < 0 || num11 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", 1, RegistryValueKind.DWord);
				num11 = 1;
			}
			if (num12 < -1 || num12 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1, RegistryValueKind.DWord);
				num12 = 1;
			}
			m_red_level = (uint)num;
			m_green_level = (uint)num2;
			m_blue_level = (uint)num3;
			m_red_level_dc = (uint)num4;
			m_green_level_dc = (uint)num5;
			m_blue_level_dc = (uint)num6;
			m_Colorful = (uint)num7;
			m_Colorful_dc = (uint)num8;
			m_BreathingLightEffect = (uint)num9;
			m_SupportRGBLightBarColorful = (uint)num10;
			m_SupportRGBLightBarBreathEffect = (uint)num11;
			m_LightBarOnOff = (uint)num12;
		}
		catch
		{
		}
	}

	private void LoadRegistryForLineStatus()
	{
		try
		{
			int red_level = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel", 9u);
			int green_level = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel", 9u);
			int blue_level = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel", 9u);
			int red_level_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel_dc", 0u);
			int green_level_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel_dc", 0u);
			int blue_level_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel_dc", 0u);
			int colorful = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful", 0);
			int colorful_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful_dc", 0);
			m_red_level = (uint)red_level;
			m_green_level = (uint)green_level;
			m_blue_level = (uint)blue_level;
			m_red_level_dc = (uint)red_level_dc;
			m_green_level_dc = (uint)green_level_dc;
			m_blue_level_dc = (uint)blue_level_dc;
			m_Colorful = (uint)colorful;
			m_Colorful_dc = (uint)colorful_dc;
		}
		catch
		{
			LogCtrl.Write(className + "[LoadRegistryForLineStatus] failed.");
		}
	}

	private void SetRegistry(string key, uint data)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, key, data, RegistryValueKind.DWord);
	}

	private int GetRegistry(string key)
	{
		string subKey = "\\OEM\\GamingCenter2";
		return (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, key, 0);
	}

	private void KeyboardcloseTimer_ControlPowerEvent(object sender, EventArgs e)
	{
		if (Convert.ToBoolean(sender))
		{
			if (m_LightBarOnOff == 1)
			{
				SetMyLightBarOnOff(0u);
			}
		}
		else if (m_LightBarOnOff == 1)
		{
			SetMyLightBarOnOff(1u);
		}
	}

	public override uint GetPowerStatus()
	{
		return m_LightBarOnOff;
	}
}
