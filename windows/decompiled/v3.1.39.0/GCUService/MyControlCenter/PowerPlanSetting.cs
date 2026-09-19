using System;
using System.Diagnostics;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class PowerPlanSetting
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_sRegistryPath = "\\OEM\\GamingCenter2\\MySetting";

	public int m_nPowerMode = 3;

	private Guid m_guid_Gaming;

	public void Init()
	{
		LoadRegistry();
		SetPowerPlanMode();
	}

	private void LoadRegistry()
	{
		int num = 0;
		string text = "";
		try
		{
			num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\PowerPlan", "Mode", 3);
			text = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\PowerPlan", "Gaming", 3);
			m_nPowerMode = num;
			m_guid_Gaming = new Guid(text);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\PowerPlan", "Mode", 3, RegistryValueKind.DWord);
			m_nPowerMode = 3;
			WritePowerOptionName();
		}
	}

	private void WritePowerOptionName()
	{
		if (EcCtrl.GetProjectIdFromEC().IsProjectId_Commercial())
		{
			m_guid_Gaming = PowerOptionAPI.powerWriteGamingModeName("MyOfficeMode");
		}
		else
		{
			m_guid_Gaming = PowerOptionAPI.powerWriteGamingModeName("MyGamingMode");
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\PowerPlan", "Gaming", m_guid_Gaming.ToString(), RegistryValueKind.String);
	}

	private void SetPowerPlanMode()
	{
		switch (m_nPowerMode)
		{
		case 1:
			GamingActive();
			break;
		case 2:
			HighPerformanceActive();
			break;
		case 3:
			BalanceActive();
			break;
		case 4:
			PowerSaverActive();
			break;
		}
	}

	public void GamingActive()
	{
		Guid SchemeGuid = m_guid_Gaming;
		PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
		m_nPowerMode = 1;
		SetRegistry("Mode", m_nPowerMode);
	}

	public void HighPerformanceActive()
	{
		Guid SchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
		PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
		m_nPowerMode = 2;
		SetRegistry("Mode", m_nPowerMode);
	}

	public void BalanceActive()
	{
		Guid SchemeGuid = new Guid("381b4222-f694-41f0-9685-ff5bb260df2e");
		PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
		m_nPowerMode = 3;
		SetRegistry("Mode", m_nPowerMode);
	}

	public void PowerSaverActive()
	{
		Guid SchemeGuid = new Guid("a1841308-3541-4fab-bc81-f71556f20b4a");
		PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
		m_nPowerMode = 4;
		SetRegistry("Mode", m_nPowerMode);
	}

	public void DeleteMyPowerPlan()
	{
		LoadRegistry();
		Guid SchemeGuid = new Guid("381b4222-f694-41f0-9685-ff5bb260df2e");
		PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
		PowerOptionAPI.DeleteScheme(m_guid_Gaming);
	}

	private void SetRegistry(string key, int data)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\PowerPlan", key, data, RegistryValueKind.DWord);
	}

	public void OnDeleteUserAllPowerPlan()
	{
		ProcessStartInfo processStartInfo = new ProcessStartInfo();
		processStartInfo.FileName = "cmd.exe";
		processStartInfo.RedirectStandardOutput = true;
		processStartInfo.RedirectStandardError = true;
		processStartInfo.RedirectStandardInput = true;
		processStartInfo.UseShellExecute = false;
		processStartInfo.CreateNoWindow = true;
		Process process = new Process();
		process.StartInfo = processStartInfo;
		process.ErrorDataReceived += cmd_Error;
		process.OutputDataReceived += cmd_DataReceived;
		process.EnableRaisingEvents = true;
		process.Start();
		process.BeginOutputReadLine();
		process.BeginErrorReadLine();
		process.StandardInput.WriteLine("powercfg /list");
		process.StandardInput.WriteLine("exit");
		process.WaitForExit();
	}

	private void cmd_DataReceived(object sender, DataReceivedEventArgs e)
	{
		Console.WriteLine(e.Data);
		DeleteGuid(e.Data);
	}

	private void cmd_Error(object sender, DataReceivedEventArgs e)
	{
		Console.WriteLine("Error from other process");
		Console.WriteLine(e.Data);
	}

	private void DeleteGuid(string data)
	{
		if (data == null || data.Length < 55)
		{
			return;
		}
		string empty = string.Empty;
		if (data.IndexOf("Power Scheme GUID", 0, 17) != 0)
		{
			return;
		}
		empty = data.Substring(19, 36);
		try
		{
			Process process = new Process();
			process.StartInfo.FileName = "cmd.exe";
			process.StartInfo.UseShellExecute = false;
			process.StartInfo.RedirectStandardOutput = true;
			process.StartInfo.RedirectStandardInput = true;
			process.StartInfo.CreateNoWindow = true;
			process.Start();
			process.StandardInput.WriteLine("powercfg -delete " + empty + "& exit");
			process.WaitForExit();
			process.Close();
		}
		catch
		{
		}
	}

	public void OnRestoredefaultschemes()
	{
		PowerOptionAPI.PowerRestoreDefaultPowerSchemes();
	}
}
