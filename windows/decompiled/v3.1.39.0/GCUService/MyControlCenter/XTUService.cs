using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using Utility;

namespace MyControlCenter;

internal class XTUService
{
	private static string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	public static void XtuInstallSvc()
	{
		try
		{
			LogCtrl.Write(className + "XtuInstallSvc Start");
			Process process = new Process();
			ProcessStartInfo processStartInfo = new ProcessStartInfo
			{
				WindowStyle = ProcessWindowStyle.Hidden,
				FileName = "XTU\\Drivers\\XtuService.exe"
			};
			process.StartInfo = processStartInfo;
			processStartInfo.Arguments = "-install";
			processStartInfo.RedirectStandardOutput = true;
			process.StartInfo.UseShellExecute = false;
			process.Start();
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "XtuInstallSvc Fail, " + ex.Message);
		}
	}

	public static void XtuUninstallSvc()
	{
		try
		{
			LogCtrl.Write(className + "XtuUninstallSvc Start");
			Process process = new Process();
			ProcessStartInfo processStartInfo = new ProcessStartInfo
			{
				WindowStyle = ProcessWindowStyle.Hidden,
				FileName = "XTU\\Drivers\\XtuService.exe"
			};
			process.StartInfo = processStartInfo;
			processStartInfo.Arguments = "-uninstall";
			processStartInfo.RedirectStandardOutput = true;
			process.StartInfo.UseShellExecute = false;
			process.Start();
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "XtuUninstallSvc Fail, " + ex.Message);
		}
	}

	public static void NetStartXtuSvc()
	{
		try
		{
			Process process = new Process();
			process.StartInfo.FileName = "cmd.exe";
			process.StartInfo.UseShellExecute = false;
			process.StartInfo.RedirectStandardInput = true;
			process.StartInfo.RedirectStandardOutput = true;
			process.StartInfo.RedirectStandardError = true;
			process.StartInfo.CreateNoWindow = true;
			process.Start();
			process.StandardInput.WriteLine("Net start Xtu3Service");
			process.Close();
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "NetStartXtuSvc Fail, " + ex.Message);
		}
	}

	public static bool XtuCLI_Command(string cmd)
	{
		bool flag = false;
		try
		{
			Process process = new Process();
			process.StartInfo = new ProcessStartInfo
			{
				WindowStyle = ProcessWindowStyle.Hidden,
				FileName = "XTU\\XtuCLI.exe",
				Arguments = cmd,
				WorkingDirectory = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName
			};
			process.Start();
			process.WaitForExit(5000);
			flag = true;
			Directory.Delete("C:\\\\XTU_xmlFiles", recursive: true);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "XtuCLI_Command Fail, cmd: " + cmd + ", " + ex.Message);
			flag = false;
		}
		return flag;
	}

	public static bool IsXtuCLISupport()
	{
		bool result = false;
		Process[] processesByName = Process.GetProcessesByName("XtuService");
		for (int i = 0; i < processesByName.Count(); i++)
		{
			result = true;
		}
		return result;
	}
}
