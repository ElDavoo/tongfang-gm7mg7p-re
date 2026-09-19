using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.NetworkInformation;
using System.Reflection;
using Utility;

namespace MyControlCenter.MySetting.ColorCalibration;

internal class ColorProfileInfo
{
	private static string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	public static string m_ICM_Server = "http://iccprofile.uniwill.com.tw/api/iccprofile/";

	public static string m_ICCProfilePath = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\ICCProfile";

	public static List<string> m_ICCProfileLists = new List<string>();

	public static ICCProfileInfo m_ICCProfileInfo = new ICCProfileInfo();

	public static string strSerialNumber { get; set; }

	public static string strMacAddress { get; set; }

	public static string GetSerialNumber()
	{
		return new SMBIOS().System.SerialNumber;
	}

	public static string GetMacAddress()
	{
		return (from n in NetworkInterface.GetAllNetworkInterfaces()
			where n.NetworkInterfaceType == NetworkInterfaceType.Ethernet && n.NetworkInterfaceType != NetworkInterfaceType.Loopback
			select n.GetPhysicalAddress()).FirstOrDefault().ToString();
	}

	public static void UpdateICCProfileInfo()
	{
		string empty = string.Empty;
		bool flag = false;
		m_ICCProfileLists = GetICCProfileLists();
		foreach (string iCCProfileList in m_ICCProfileLists)
		{
			try
			{
				if (!flag)
				{
					empty = m_ICCProfilePath + "\\" + iCCProfileList.ToString() + ".icm";
					if (File.Exists(empty) && new FileInfo(empty).Length != 0L)
					{
						LogCtrl.Write(m_className + "[UpdateICCProfileInfo] Find local profile.");
						flag = true;
						m_ICCProfileInfo.bFileExist = true;
						m_ICCProfileInfo.sFileName = iCCProfileList.ToString();
					}
				}
			}
			catch (Exception ex)
			{
				LogCtrl.Write(m_className + "[UpdateICCProfileInfo] " + ex.ToString());
			}
		}
	}

	private static List<string> GetICCProfileLists()
	{
		List<string> list = new List<string>();
		try
		{
			IEnumerator enumerator = DisplayDetails.GetMonitorDetails().GetEnumerator();
			int num = 0;
			while (enumerator.MoveNext())
			{
				DisplayDetails displayDetails = (DisplayDetails)enumerator.Current;
				if (displayDetails.Model == "")
				{
					list.Add(displayDetails.MonitorID + "_" + strSerialNumber);
					list.Add(displayDetails.MonitorID + "_" + strMacAddress);
					LogCtrl.Write(m_className + "[GetICCProfileLists] List = " + displayDetails.MonitorID + "_" + strSerialNumber);
					LogCtrl.Write(m_className + "[GetICCProfileLists] List = " + displayDetails.MonitorID + "_" + strMacAddress);
				}
				num++;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + "[GetICCProfileLists] List = " + ex.ToString());
		}
		return list;
	}
}
