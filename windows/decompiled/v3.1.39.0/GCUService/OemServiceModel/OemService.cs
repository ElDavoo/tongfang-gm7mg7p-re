using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

namespace OemServiceModel;

public static class OemService
{
	public static string m_sOemCustomerCmd = "";

	[DllImport("OemServiceWinApp.dll", CallingConvention = CallingConvention.StdCall, CharSet = CharSet.Ansi)]
	public static extern bool OemSvcHook(int lenCmd, string[] bufferCmd, IntPtr buuferRead, int ReadSize);

	public static void Exec(int lenCmd, string[] bufferCmd, int lenRead, byte[] bufferRead)
	{
		try
		{
			IntPtr intPtr = Marshal.AllocHGlobal(lenRead);
			OemSvcHook(lenCmd, bufferCmd, intPtr, lenRead);
			Marshal.Copy(intPtr, bufferRead, 0, lenRead);
			Marshal.FreeHGlobal(intPtr);
		}
		catch
		{
		}
	}

	public static string Read(string cmd)
	{
		try
		{
			Process process = new Process();
			ProcessStartInfo processStartInfo = new ProcessStartInfo();
			processStartInfo.WindowStyle = ProcessWindowStyle.Hidden;
			processStartInfo.FileName = "OemServiceWinApp.exe";
			process.StartInfo = processStartInfo;
			processStartInfo.Arguments = cmd + m_sOemCustomerCmd;
			processStartInfo.RedirectStandardOutput = true;
			processStartInfo.WorkingDirectory = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName;
			process.StartInfo.UseShellExecute = false;
			process.StartInfo.CreateNoWindow = true;
			process.Start();
			string result = process.StandardOutput.ReadToEnd();
			process.WaitForExit(5000);
			return result;
		}
		catch
		{
			return null;
		}
	}

	public static void Write(string cmd)
	{
		try
		{
			Process process = new Process();
			process.StartInfo = new ProcessStartInfo
			{
				WindowStyle = ProcessWindowStyle.Hidden,
				FileName = "OemServiceWinApp.exe",
				Arguments = cmd + m_sOemCustomerCmd,
				WorkingDirectory = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName
			};
			process.Start();
			process.WaitForExit(5000);
		}
		catch
		{
		}
	}

	public static bool HasFeature(string cmd)
	{
		if (Read("Help").Contains("=>" + cmd + " : "))
		{
			return true;
		}
		return false;
	}

	public static void CheckOemCostomerListSupport()
	{
		int num = 0;
		m_sOemCustomerCmd = "";
		try
		{
			string text = Read("setapctrl /GetStatus");
			string text2 = "";
			string text3 = "";
			string text4 = "";
			if (text.Substring(285, 1) == " ")
			{
				text2 = text.Substring(290, 1);
			}
			if (text2 == " ")
			{
				text3 = text.Substring(295, 1);
			}
			if (text3 == " ")
			{
				text4 = text.Substring(300, 1);
			}
			if (text4 == " ")
			{
				num = Convert.ToInt16(text.Substring(303, 2), 16);
			}
		}
		catch
		{
		}
		if (num == 1)
		{
			m_sOemCustomerCmd = " /GGYY7878";
		}
	}
}
