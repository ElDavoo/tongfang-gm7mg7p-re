using System;
using System.Threading.Tasks;
using Microsoft.Win32;

namespace OemServiceModel;

public static class Tdr
{
	public static void Set()
	{
		Task.Run(delegate
		{
			try
			{
				uint num = Convert.ToUInt32(OemService.Read("OemTdr /GetTdr").Substring(249, 3));
				if (num != 0 || num < 255)
				{
					if (Environment.Is64BitProcess)
					{
						RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
					}
					else
					{
						RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
					}
				}
			}
			catch
			{
			}
		});
	}
}
