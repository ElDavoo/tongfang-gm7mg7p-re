using System.Text;
using System.Threading;
using Microsoft.Win32;
using MyECIO;
using UsbHidModel;
using Utility;

namespace MyControlCenter;

public class MyTouchPadManager
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_RegistryPath = "\\OEM\\GamingCenter2\\MyTouchPad";

	private int m_TopLevel;

	private int m_LeftLevel;

	private int m_RightLevel;

	private int m_TopInterval = 5;

	private int m_LeftInterval = 5;

	private int m_RightInterval = 5;

	private const ushort PIXART_VID = 2362;

	private const ushort PIXART_PID = 597;

	private const ushort PIXART_PID_IDM = 628;

	private HIDManager m_hid;

	public virtual void EnableByService()
	{
	}

	public virtual void Disable()
	{
	}

	public virtual async void Receive(byte[] data)
	{
		string text = ((dynamic)(await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data))))["Action"];
		_ = string.Empty;
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyTouchPad\\MyTouchPadManager.cs", 56);
		LogCtrl.TraceMessage("[Receive] msg = " + text, "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyTouchPad\\MyTouchPadManager.cs", 57);
	}

	public virtual void UpdateStatusToClient()
	{
		var data = new
		{
			TopLevel = m_TopLevel.ToString(),
			LeftLevel = m_LeftLevel.ToString(),
			RightLevel = m_RightLevel.ToString(),
			TopInterval = m_TopInterval.ToString(),
			LeftInterval = m_LeftInterval.ToString(),
			RightInterval = m_RightInterval.ToString()
		};
		App.m_MQTTService.Publish("TouchPadWorkArea/Status", data, retain: false);
	}

	public virtual void Resume()
	{
	}

	public virtual void Uninstall()
	{
	}

	public virtual void Restore()
	{
	}

	private void SetDefault()
	{
	}

	private void LoadRegistry()
	{
		try
		{
			m_TopLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "TopLevel", 0u);
			m_LeftLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "LeftLevel", 0u);
			m_RightLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "RightLevel", 0u);
		}
		catch
		{
			LoadDefault();
		}
	}

	private void LoadDefault()
	{
		m_TopLevel = 0;
		m_LeftLevel = 0;
		m_RightLevel = 0;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TopLevel", m_TopLevel, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "LeftLevel", m_LeftLevel, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "RightLevel", m_RightLevel, RegistryValueKind.DWord);
	}

	private void Init()
	{
	}

	private void SetTopLevel(int level)
	{
		m_TopLevel = level;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TopLevel", level, RegistryValueKind.DWord);
		SetCurtain(TPCurtain_Direction.Top, level);
	}

	private void SetLeftLevel(int level)
	{
		m_LeftLevel = level;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "LeftLevel", level, RegistryValueKind.DWord);
		SetCurtain(TPCurtain_Direction.Left, level);
	}

	private void SetRightLevel(int level)
	{
		m_RightLevel = level;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "RightLevel", level, RegistryValueKind.DWord);
		SetCurtain(TPCurtain_Direction.Right, level);
	}

	public void Init_IDM_TouchPadSetting()
	{
		m_hid = new HIDManager();
		ushort uSAGE = 1;
		m_hid.Init(2362, 628, uSAGE);
	}

	public void InitTouchPadSetting()
	{
		m_hid = new HIDManager();
		ushort uSAGE = 1;
		if (m_hid.Init(2362, 597, uSAGE))
		{
			EnableWorkingArea();
		}
	}

	public void EnableWorkingArea()
	{
		byte[] array = new byte[4] { 67, 96, 18, 0 };
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		m_hid.GetFeature(array);
		if (array[0] == 67 && array[1] == 96 && array[2] == 2)
		{
			byte b = (byte)(array[3] | 2);
			array[2] = 2;
			array[3] = b;
			m_hid.WriteFeature(array);
			Thread.Sleep(1);
			array[2] = 18;
			array[3] = 0;
			m_hid.GetFeature(array);
			if (array[3] == b)
			{
				LogCtrl.TraceMessage("Enable Super-Curtain Success", "EnableWorkingArea", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyTouchPad\\MyTouchPadManager.cs", 229);
			}
		}
	}

	public byte ReadFWtype()
	{
		byte[] array = new byte[4] { 67, 4, 16, 0 };
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		m_hid.GetFeature(array);
		return array[3];
	}

	public void SetCurtain(TPCurtain_Direction direction, int level)
	{
		byte b = 28;
		switch (level)
		{
		default:
			LogCtrl.TraceMessage("TouchPadSetting, setting level is overflow", "SetCurtain", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyTouchPad\\MyTouchPadManager.cs", 251);
			return;
		case 1:
		case 2:
		case 3:
		case 4:
		case 5:
		case 6:
		case 7:
		case 8:
		case 9:
			b = (byte)((level + 1) * 25);
			break;
		case 0:
			break;
		}
		byte b2 = 0;
		switch (direction)
		{
		case TPCurtain_Direction.Left:
			b2 = 22;
			break;
		case TPCurtain_Direction.Top:
			b2 = 20;
			break;
		case TPCurtain_Direction.Right:
			b2 = 23;
			break;
		}
		byte[] array = new byte[4] { 67, b2, 3, b };
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		array[2] = 19;
		array[3] = 0;
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		m_hid.GetFeature(array);
		_ = array[3];
	}

	public void HalfToggle_Enable()
	{
		byte[] array = new byte[4] { 67, 7, 19, 0 };
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		m_hid.GetFeature(array);
		byte b = (byte)(array[3] & 0xFD);
		array[2] = 3;
		array[3] = b;
		m_hid.WriteFeature(array);
	}

	public void HalfToggle_Disable()
	{
		byte[] array = new byte[4] { 67, 7, 19, 0 };
		m_hid.WriteFeature(array);
		Thread.Sleep(1);
		m_hid.GetFeature(array);
		byte b = (byte)(array[3] | 2);
		array[2] = 3;
		array[3] = b;
		m_hid.WriteFeature(array);
	}
}
