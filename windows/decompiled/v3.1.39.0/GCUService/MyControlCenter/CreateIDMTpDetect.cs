using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Microsoft.Win32;
using Utility;

namespace MyControlCenter;

public static class CreateIDMTpDetect
{
	public static void Start()
	{
		End();
		try
		{
			string text = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\ItemSupport\\", "BIOS_PROJECT_ID", null, RegistryValueKind.String);
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\ItemSupport\\", "HalfTPSupport", 0, RegistryValueKind.DWord);
			if (text != null && !(text != "IDM") && num == 1)
			{
				Process.Start(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\IDM_Touch_OSD.exe");
			}
		}
		catch
		{
		}
	}

	public static void End()
	{
		try
		{
			Process[] processesByName = Process.GetProcessesByName("IDM_Touch_OSD");
			for (int i = 0; i < processesByName.Count(); i++)
			{
				processesByName[i].Kill();
			}
		}
		catch
		{
		}
	}

	public static void WriteOSDLangFile(string status)
	{
		try
		{
			FileStream fileStream = new FileStream(Environment.GetFolderPath(Environment.SpecialFolder.CommonDocuments) + "\\lang.txt", FileMode.Create);
			StreamWriter streamWriter = new StreamWriter(fileStream, Encoding.Unicode);
			streamWriter.Write(status);
			streamWriter.Close();
			fileStream.Close();
		}
		catch (Exception ex)
		{
			LogCtrl.Write(ex.ToString());
		}
	}
}
