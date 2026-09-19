using System;
using System.Threading.Tasks;
using Microsoft.Win32;
using Utility;

namespace MyControlCenter;

public static class Tdr2
{
	public static void Set()
	{
		Task.Run(delegate
		{
			try
			{
				uint num = Convert.ToUInt32(NvramVariable.GetFwVars().TDRdata);
				if (num != 0 && num < 255)
				{
					LogCtrl.TraceMessage("Check Factory TDR function, NvramVariable TDRdata data: " + num + ", then write registry.", "Set", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 1107);
					if (Environment.Is64BitProcess)
					{
						RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
					}
					else
					{
						RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
					}
				}
				else
				{
					LogCtrl.TraceMessage("Check Factory TDR function, NvramVariable TDRdata data: " + num + ", then do noyhing.", "Set", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 1115);
				}
			}
			catch (Exception ex)
			{
				LogCtrl.TraceMessage("Check Factory TDR function Failed " + ex.ToString(), "Set", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\NvramVariable.cs", 1120);
			}
		});
	}
}
