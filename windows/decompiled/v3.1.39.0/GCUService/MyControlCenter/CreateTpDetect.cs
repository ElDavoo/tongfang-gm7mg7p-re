using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Utility;

namespace MyControlCenter;

public static class CreateTpDetect
{
	public static void Start()
	{
		End();
		try
		{
			CreateProcessAsUserWrapper.LaunchChildProcess(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\OSDTpDetect.exe");
		}
		catch
		{
		}
	}

	public static void End()
	{
		try
		{
			Process[] processesByName = Process.GetProcessesByName("OSDTpDetect");
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
