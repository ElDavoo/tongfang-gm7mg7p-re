using System;
using System.Collections;
using System.Collections.Generic;
using System.Management;
using System.Management.Instrumentation;
using System.Text;
using Microsoft.Win32;

namespace MyControlCenter.MySetting.ColorCalibration;

internal class DisplayDetails
{
	[ManagementKey]
	public string PnPID { get; set; }

	[ManagementProbe]
	public string SerialNumber { get; set; }

	[ManagementProbe]
	public string Model { get; set; }

	[ManagementProbe]
	public string MonitorID { get; set; }

	[ManagementProbe]
	public string Name { get; set; }

	[ManagementProbe]
	public string SizeDiagInch { get; set; }

	[ManagementProbe]
	public string SizeHorCM { get; set; }

	[ManagementProbe]
	public string SizeVerCM { get; set; }

	[ManagementProbe]
	public string Manufacuter { get; set; }

	public DisplayDetails(string sManufacturer, string sPnPID, string sSerialNumber, string sModel, string sMonitorID, string sName, string sSize, string sHSize, string sVSize)
	{
		PnPID = sPnPID;
		SerialNumber = sSerialNumber;
		Model = sModel;
		MonitorID = sMonitorID;
		Name = sName;
		SizeDiagInch = sSize;
		SizeHorCM = sHSize;
		SizeVerCM = sVSize;
		Manufacuter = sManufacturer;
	}

	[ManagementEnumerator]
	public static IEnumerable GetMonitorDetails()
	{
		List<string> sKeys = new List<string>();
		ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher("root\\cimv2", "SELECT * FROM Win32_PnPEntity WHERE Service = 'monitor'");
		foreach (ManagementObject item in managementObjectSearcher.Get())
		{
			string text = "";
			string text2 = "";
			string sSize = "";
			string sHSize = "";
			string sVSize = "";
			string text3;
			string text4;
			string text5;
			string text6;
			try
			{
				text3 = item["Manufacturer"].ToString();
				text4 = item["PNPDeviceID"].ToString();
				sKeys.Add("SYSTEM\\CurrentControlSet\\Enum\\" + text4 + "\\Device Parameters");
				string name = "SYSTEM\\CurrentControlSet\\Enum\\" + text4 + "\\Device Parameters";
				RegistryKey registryKey = Registry.LocalMachine.OpenSubKey(name, writable: false);
				text5 = item["Name"].ToString();
				text6 = ((string[])item["HardwareID"])[0].ToString().Replace("MONITOR\\", "");
				string value = new string(new char[4] { '\0', '\0', '\0', 'ÿ' });
				string value2 = new string(new char[4] { '\0', '\0', '\0', 'ü' });
				if (registryKey.GetValue("EDID", null) is byte[] array)
				{
					string[] array2 = new string[4]
					{
						Encoding.Default.GetString(array, 54, 18),
						Encoding.Default.GetString(array, 72, 18),
						Encoding.Default.GetString(array, 90, 18),
						Encoding.Default.GetString(array, 108, 18)
					};
					try
					{
						double num = double.Parse(((byte)array.GetValue(21)).ToString());
						double num2 = double.Parse(((byte)array.GetValue(22)).ToString());
						sHSize = num.ToString();
						sVSize = num2.ToString();
						sSize = Math.Round(Math.Sqrt(num * num + num2 * num2) * 0.3937007874015748, 1).ToString();
					}
					catch
					{
					}
					string[] array3 = array2;
					foreach (string text7 in array3)
					{
						if (text7.Contains(value))
						{
							text = text7.Substring(4).Replace("\0", "").Trim();
						}
						if (text7.Contains(value2))
						{
							text2 = text7.Substring(4).Replace("\0", "").Trim();
						}
					}
				}
			}
			catch
			{
				continue;
			}
			if (!string.IsNullOrEmpty(text3 + text4 + text + text2 + text6 + text5))
			{
				yield return new DisplayDetails(text3, text4, text, text2, text6, text5, sSize, sHSize, sVSize);
			}
		}
	}
}
