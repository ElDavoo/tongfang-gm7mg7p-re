using System;
using System.Text;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class MyRgbLightbarManager
{
	private MyRgbLightbarView m_View = new MyRgbLightbarView();

	private string m_path = "\\OEM\\GamingCenter2\\MyLightBar";

	private uint m_LightBarOnOff = 1u;

	private uint m_red_level = 9u;

	private uint m_green_level = 9u;

	private uint m_blue_level = 9u;

	private uint m_red_level_dc;

	private uint m_green_level_dc;

	private uint m_blue_level_dc;

	private uint m_Colorful = 1u;

	private uint m_Colorful_dc;

	private uint m_BreathingLightEffect = 1u;

	private uint m_SupportRGBLightBarColorful = 1u;

	private uint m_SupportRGBLightBarBreathEffect = 1u;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private KeyboardCloseTimer keyboardcloseTimer = KeyboardCloseTimer.CreateInstance;

	public virtual void Enable()
	{
		LoadRegistry();
		RGBLightBarTable.Init(MyRgbLightBarDefault.GetProjectIdFromEC());
		SetApExist(1);
		SetMyLightBarOnOff(m_LightBarOnOff);
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			SetOEMService(m_LightBarOnOff, m_Colorful_dc);
		}
		else
		{
			SetOEMService(m_LightBarOnOff, m_Colorful);
		}
		SetBreathingLightEffect(m_BreathingLightEffect);
		ValueChanged(PowerModeEvent.g_ACLineStatus);
		keyboardcloseTimer.ControlBrigtnessEvent += KeyboardcloseTimer_ControlPowerEvent;
	}

	public virtual void Disable()
	{
		SetApExist(0);
	}

	public virtual async void Recieve(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[Recieve] msg = " + text);
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
			UserSetColorful(text);
			UpdateStatusToClient(1);
			break;
		case "BREATHINGLIGHT":
			UserSetBreathingLight();
			UpdateStatusToClient(1);
			break;
		}
	}

	public virtual void UpdateStatusToClient(int run)
	{
		if (run != 0)
		{
			uint num = 0u;
			num = ((PowerModeEvent.g_ACLineStatus != 0) ? m_Colorful : m_Colorful_dc);
			var data = new
			{
				POWER = m_LightBarOnOff.ToString(),
				RL = m_red_level.ToString(),
				GL = m_green_level.ToString(),
				BL = m_blue_level.ToString(),
				RL_DC = m_red_level_dc.ToString(),
				GL_DC = m_green_level_dc.ToString(),
				BL_DC = m_blue_level_dc.ToString(),
				COLORFUL = num.ToString(),
				BREATHINGLIGHT = m_BreathingLightEffect.ToString(),
				ACLINESTATUS = PowerModeEvent.g_ACLineStatus.ToString()
			};
			m_View.SendStatusToClient(data);
		}
	}

	public virtual void Resume()
	{
		SetApExist(1);
		LoadRegistry();
		SetMyLightBarOnOff(m_LightBarOnOff);
		SetBreathingLightEffect(m_BreathingLightEffect);
		ValueChanged(PowerModeEvent.g_ACLineStatus);
	}

	public virtual void OnModernStandby()
	{
	}

	public virtual void PowerStatusChange(int mode)
	{
		LoadRegistryForLineStatus();
		ValueChanged(mode);
		if (mode == 0)
		{
			SetOEMService(m_LightBarOnOff, m_Colorful_dc);
		}
		else
		{
			SetOEMService(m_LightBarOnOff, m_Colorful);
		}
	}

	public virtual void Suspend()
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("MyRgbLightbarManager | Suspend");
	}

	public virtual void Uninstall()
	{
		string subKey = "\\OEM\\GamingCenter2";
		try
		{
			if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1) != -1)
			{
				RegistryCtrl.RegistrySoftwareSubKeyTreeDelete(RegistryHive.LocalMachine, subKey, "MyLightBar");
			}
			LogCtrl.Write("MyRgbLightbarManager | Uninstall | Delete Registry OK!");
		}
		catch
		{
			LogCtrl.Write("MyRgbLightbarManager | Uninstall | No Registry!");
		}
	}

	public virtual void Default()
	{
		LogCtrl.Write("[Default] Start");
		MyRgbLightBarDefault.OnDefaultFromCustomize(RegistryCtrl.GetCustomizeTarget(), bRecoverReg: true, bRecoverEC: false, PowerModeEvent.g_ACLineStatus);
		LoadRegistry();
		SetMyLightBarOnOff(m_LightBarOnOff);
		SetBreathingLightEffect(m_BreathingLightEffect);
		ValueChanged(PowerModeEvent.g_ACLineStatus);
		LogCtrl.Write("[Default] End");
	}

	private void Save()
	{
		LogCtrl.Write("[Save] Start");
		if (m_SupportRGBLightBarColorful == 1)
		{
			SetRegistry("Colorful", m_Colorful);
			SetRegistry("Colorful_dc", m_Colorful_dc);
		}
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			SetOEMService(m_LightBarOnOff, m_Colorful_dc);
		}
		else
		{
			SetOEMService(m_LightBarOnOff, m_Colorful);
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
		LogCtrl.Write("[Save] End");
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
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			SetOEMService(status, m_Colorful_dc);
		}
		else
		{
			SetOEMService(status, m_Colorful);
		}
		SetRegistry("LightBarOnOff", status);
	}

	private void UserSetColorful(string msg)
	{
		if (m_SupportRGBLightBarColorful == 0)
		{
			return;
		}
		if (PowerModeEvent.g_ACLineStatus == 0)
		{
			if (!(msg == "COLORFUL_ON"))
			{
				if (msg == "COLORFUL_OFF")
				{
					m_Colorful_dc = 0u;
				}
			}
			else
			{
				m_Colorful_dc = 1u;
			}
			SetOEMService(m_LightBarOnOff, m_Colorful_dc);
			SetRegistry("Colorful_dc", m_Colorful_dc);
		}
		else
		{
			if (!(msg == "COLORFUL_ON"))
			{
				if (msg == "COLORFUL_OFF")
				{
					m_Colorful = 0u;
				}
			}
			else
			{
				m_Colorful = 1u;
			}
			SetOEMService(m_LightBarOnOff, m_Colorful);
			SetRegistry("Colorful", m_Colorful);
		}
		ValueChanged(PowerModeEvent.g_ACLineStatus);
	}

	private void UserSetBreathingLight()
	{
		if (m_SupportRGBLightBarBreathEffect != 0)
		{
			if (m_BreathingLightEffect == 1)
			{
				m_BreathingLightEffect = 0u;
			}
			else
			{
				m_BreathingLightEffect = 1u;
			}
			SetBreathingLightEffect(m_BreathingLightEffect);
			SetRegistry("BreathingLightEffect", m_BreathingLightEffect);
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
				break;
			case "GL":
				m_green_level = level;
				break;
			case "BL":
				m_blue_level = level;
				break;
			case "RL_DC":
				m_red_level_dc = level;
				SetRedLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			case "GL_DC":
				m_green_level_dc = level;
				SetGreenLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			case "BL_DC":
				m_blue_level_dc = level;
				SetBlueLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			}
		}
		else
		{
			switch (key)
			{
			case "RL":
				m_red_level = level;
				SetRedLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			case "GL":
				m_green_level = level;
				SetGreenLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			case "BL":
				m_blue_level = level;
				SetBlueLevel(level, bWriteToECRam: true, bWriteToReg: true, bWriteToOem: true);
				break;
			case "RL_DC":
				m_red_level_dc = level;
				break;
			case "GL_DC":
				m_green_level_dc = level;
				break;
			case "BL_DC":
				m_blue_level_dc = level;
				break;
			}
		}
	}

	private void ValueChanged(int mode)
	{
		switch (mode)
		{
		case 0:
			LogCtrl.Write($"MyRgbLightbarManager | ValueChanged | OffLine");
			if (m_Colorful_dc == 0)
			{
				SetRedLevel(m_red_level_dc, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetGreenLevel(m_green_level_dc, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetBlueLevel(m_blue_level_dc, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
			}
			else
			{
				SetRedLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetGreenLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetBlueLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
			}
			SetColorful(m_Colorful_dc);
			break;
		case 1:
			LogCtrl.Write($"MyRgbLightbarManager | ValueChanged | OnLine");
			if (m_Colorful == 0)
			{
				SetRedLevel(m_red_level, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetGreenLevel(m_green_level, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetBlueLevel(m_blue_level, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
			}
			else
			{
				SetRedLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetGreenLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
				SetBlueLevel(0u, bWriteToECRam: true, bWriteToReg: false, bWriteToOem: false);
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
			LogCtrl.Write("MyRgbLightbarManager | SetColorful | 0x0748.7 = 1 WelcomeMode ON");
		}
		else
		{
			byte data2 = (byte)(b & 0x7F);
			EcCtrl.Write(GetType().Name, 1864, data2);
			LogCtrl.Write("MyRgbLightbarManager | SetColorful | 0x0748.7 = 0 WelcomeMode OFF");
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
		else if (m_LightBarOnOff != 0)
		{
			byte data2 = (byte)(b & 0xF7);
			EcCtrl.Write(GetType().Name, 1864, data2);
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
				b = ((m_BreathingLightEffect != 1) ? ((byte)(b | 8)) : ((byte)(b & 0xF7)));
				break;
			case 0u:
				b |= 4;
				b |= 8;
				break;
			}
			EcCtrl.Write(GetType().Name, 1864, b);
		}
		catch
		{
			LogCtrl.Write("MyRgbLightbarManager | SetMyLightBarOnOff fail.");
		}
	}

	private void SetOEMService(uint _LightBarOnOff, uint _WelcomeMode)
	{
		uint num = 1u;
		num = SetOEMService_NvramVariable(_LightBarOnOff, _WelcomeMode);
		SetRegistry("OemsvcMode", num);
	}

	private uint SetOEMService_NvramVariable(uint _LightBarOnOff, uint _WelcomeMode)
	{
		byte b = 1;
		uint num = 0u;
		uint num2 = 0u;
		uint num3 = 0u;
		byte red = 0;
		byte green = 0;
		byte blue = 0;
		if (_LightBarOnOff == 1)
		{
			if (_WelcomeMode == 1)
			{
				b = 1;
			}
			else
			{
				if (PowerModeEvent.g_ACLineStatus == 0)
				{
					num = m_red_level_dc;
					num2 = m_green_level_dc;
					num3 = m_blue_level_dc;
				}
				else
				{
					num = m_red_level;
					num2 = m_green_level;
					num3 = m_blue_level;
				}
				red = (byte)RGBLightBarTable.GetTable("Red", num);
				green = (byte)RGBLightBarTable.GetTable("Green", num2);
				blue = (byte)RGBLightBarTable.GetTable("Blue", num3);
				b = 254;
			}
		}
		else
		{
			b = 0;
		}
		NvramVariable.SetFwVars_RGBLightbar(b, red, green, blue);
		return Convert.ToUInt32(b);
	}

	private void SetApExist(int mode)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1864, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		b = ((mode != 0) ? ((byte)(b | 1)) : ((byte)(b & 0xFE)));
		EcCtrl.Write(GetType().Name, 1864, b);
		LogCtrl.Write($"MyRgbLightbarManager | SetApExist | After SetApExist, AP read 0x0748h = 0x{b:X}");
	}

	private void SetRedLevel(uint level, bool bWriteToECRam, bool bWriteToReg, bool bWriteToOem)
	{
		ulong num = 0uL;
		num = RGBLightBarTable.GetTable("Red", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format("MyRgbLightbarManager | SetRedLevel = {0}, 0x0749h = {0}", level, num));
			EcCtrl.Write(GetType().Name, 1865, (byte)num);
		}
		if (bWriteToReg)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetRegistry("RedLevel_dc", m_red_level_dc);
			}
			else
			{
				SetRegistry("RedLevel", m_red_level);
			}
		}
		if (bWriteToOem)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetOEMService(m_LightBarOnOff, m_Colorful_dc);
			}
			else
			{
				SetOEMService(m_LightBarOnOff, m_Colorful);
			}
		}
	}

	private void SetGreenLevel(uint level, bool bWriteToECRam, bool bWriteToReg, bool bWriteToOem)
	{
		ulong num = 0uL;
		num = RGBLightBarTable.GetTable("Green", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format("MyRgbLightbarManager | SetGreenLevel = {0}, 0x074Ah = {0}", level, num));
			EcCtrl.Write(GetType().Name, 1866, (byte)num);
		}
		if (bWriteToReg)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetRegistry("GreenLevel_dc", m_green_level_dc);
			}
			else
			{
				SetRegistry("GreenLevel", m_green_level);
			}
		}
		if (bWriteToOem)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetOEMService(m_LightBarOnOff, m_Colorful_dc);
			}
			else
			{
				SetOEMService(m_LightBarOnOff, m_Colorful);
			}
		}
	}

	private void SetBlueLevel(uint level, bool bWriteToECRam, bool bWriteToReg, bool bWriteToOem)
	{
		ulong num = 0uL;
		num = RGBLightBarTable.GetTable("Blue", level);
		if (bWriteToECRam)
		{
			LogCtrl.Write(string.Format("MyRgbLightbarManager | SetBlueLevel = {0}, 0x074Bh = {0}", level, num));
			EcCtrl.Write(GetType().Name, 1867, (byte)num);
		}
		if (bWriteToReg)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetRegistry("BlueLevel_dc", m_blue_level_dc);
			}
			else
			{
				SetRegistry("BlueLevel", m_blue_level);
			}
		}
		if (bWriteToOem)
		{
			if (PowerModeEvent.g_ACLineStatus == 0)
			{
				SetOEMService(m_LightBarOnOff, m_Colorful_dc);
			}
			else
			{
				SetOEMService(m_LightBarOnOff, m_Colorful);
			}
		}
	}

	private void SetTriggerBit4()
	{
		try
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1864, ref Data);
			byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
			LogCtrl.Write($"MyRgbLightbarManager | SetTriggerBit4 | Before SetTriggerBit4, AP read 0x0748h = 0x{b:X}");
			b |= 0x10;
			EcCtrl.Write(GetType().Name, 1864, b);
			LogCtrl.Write($"MyRgbLightbarManager | SetTriggerBit4 | After SetTriggerBit4, AP read 0x0748h = 0x{b:X}");
		}
		catch
		{
			Console.WriteLine("MyRgbLightbarManager | SetTriggerBit4 failed.");
		}
	}

	private void SetTriggerBit5()
	{
		try
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1864, ref Data);
			byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
			LogCtrl.Write($"MyRgbLightbarManager | SetTriggerBit5 | Before SetTriggerBit5, AP read 0x0748h = 0x{b:X}");
			b |= 0x20;
			EcCtrl.Write(GetType().Name, 1864, b);
			LogCtrl.Write($"MyRgbLightbarManager | SetTriggerBit5 | After SetTriggerBit5, AP read 0x0748h = 0x{b:X}");
		}
		catch
		{
			Console.WriteLine("MyRgbLightbarManager | SetTriggerBit5 failed.");
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
			int num7 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful", 1);
			int num8 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful_dc", 0);
			int num9 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BreathingLightEffect", 1);
			int num10 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "OemsvcMode", 1);
			int num11 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", 1);
			int num12 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", 1);
			int num13 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1);
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
				num7 = 1;
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
			if (num10 < 0 || num10 > 255)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "OemsvcMode", 1, RegistryValueKind.DWord);
				num10 = 1;
			}
			if (num11 < 0 || num11 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", 1, RegistryValueKind.DWord);
				num11 = 1;
			}
			if (num12 < 0 || num12 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", 1, RegistryValueKind.DWord);
				num12 = 1;
			}
			if (num13 < -1 || num13 > 1)
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1, RegistryValueKind.DWord);
				num13 = 1;
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
			m_SupportRGBLightBarColorful = (uint)num11;
			m_SupportRGBLightBarBreathEffect = (uint)num12;
			m_LightBarOnOff = (uint)num13;
		}
		catch
		{
			MyRgbLightBarDefault.UpdateParams(MyRgbLightBarDefault.GetProjectIdFromEC(), RegistryCtrl.GetCustomizeTarget());
			MyRgbLightBarDefault.RecoverReg();
			m_LightBarOnOff = (uint)MyRgbLightBarDefault.m_nLightBarOnOff;
			m_red_level = MyRgbLightBarDefault.m_nRedLevel;
			m_green_level = MyRgbLightBarDefault.m_nGreenLevel;
			m_blue_level = MyRgbLightBarDefault.m_nBlueLevel;
			m_red_level_dc = MyRgbLightBarDefault.m_nBlueLevel_dc;
			m_green_level_dc = MyRgbLightBarDefault.m_nGreenLevel_dc;
			m_blue_level_dc = MyRgbLightBarDefault.m_nBlueLevel_dc;
			m_Colorful = MyRgbLightBarDefault.m_nColorful;
			m_Colorful_dc = MyRgbLightBarDefault.m_nColorful_dc;
			m_BreathingLightEffect = MyRgbLightBarDefault.m_nBreathingLightEffect;
			m_SupportRGBLightBarColorful = (uint)MyRgbLightBarDefault.m_nSupportRGBLightBarColorful;
			m_SupportRGBLightBarBreathEffect = (uint)MyRgbLightBarDefault.m_nSupportRGBLightBarBreathEffect;
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
			int colorful = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful", 1);
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
			LogCtrl.Write("MyRgbLightbarManager | LoadRegistryForLineStatus failed.");
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

	public virtual uint GetPowerStatus()
	{
		return m_LightBarOnOff;
	}
}
