using System;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Net;
using System.Reflection;
using MyControlCenter;
using MyControlCenter.MySetting.ColorCalibration;
using Utility;

namespace GCUService.Workaround;

public static class Wkd_SupportColorCalibration
{
	private static string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	public static void Init()
	{
		ColorProfileInfo.strSerialNumber = ColorProfileInfo.GetSerialNumber();
		ColorProfileInfo.strMacAddress = ColorProfileInfo.GetMacAddress();
		ColorProfileInfo.UpdateICCProfileInfo();
		if (!ColorProfileInfo.m_ICCProfileInfo.bFileExist)
		{
			CheckForInternetConnection();
		}
		else
		{
			CustomizeInfo.m_supportColorCalibration = 1;
		}
	}

	private static void DownloadProfile(string filename)
	{
		if (!Directory.Exists(ColorProfileInfo.m_ICCProfilePath))
		{
			Directory.CreateDirectory(ColorProfileInfo.m_ICCProfilePath);
		}
		for (int i = 0; i < ColorProfileInfo.m_ICCProfileLists.Count(); i++)
		{
			WebClient webClient = new WebClient();
			webClient.DownloadFileCompleted += DownloadProfile_DownloadFileCompleted;
			webClient.DownloadFileTaskAsync(new Uri(ColorProfileInfo.m_ICM_Server + ColorProfileInfo.m_ICCProfileLists[i].ToString()), ColorProfileInfo.m_ICCProfilePath + "\\" + ColorProfileInfo.m_ICCProfileLists[i].ToString() + ".icm");
		}
	}

	private static void DownloadProfile_DownloadFileCompleted(object sender, AsyncCompletedEventArgs e)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		_ = string.Empty;
		if (e.Error == null)
		{
			LogCtrl.Write(m_className + "[DownloadProfile_DownloadFileCompleted] OK");
			{
				foreach (string iCCProfileList in ColorProfileInfo.m_ICCProfileLists)
				{
					if (new FileInfo(ColorProfileInfo.m_ICCProfilePath + "\\" + iCCProfileList.ToString() + ".icm").Length != 0L)
					{
						CustomizeInfo.m_supportColorCalibration = 1;
					}
				}
				return;
			}
		}
		LogCtrl.Write(m_className + "[DownloadProfile_DownloadFileCompleted] Error");
	}

	private static void CheckForInternetConnection()
	{
		ReportAvailability();
		NetworkStatus.AvailabilityChanged += DoAvailabilityChanged;
	}

	private static void DoAvailabilityChanged(object sender, NetworkStatusChangedArgs e)
	{
		ColorProfileInfo.UpdateICCProfileInfo();
		if (ColorProfileInfo.m_ICCProfileInfo.bFileExist)
		{
			NetworkStatus.AvailabilityChanged -= DoAvailabilityChanged;
		}
		ReportAvailability();
	}

	private static void ReportAvailability()
	{
		if (NetworkStatus.IsAvailable)
		{
			LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
			LogCtrl.Write(m_className + "[ReportAvailability] Network is available, Download profile.");
			DownloadProfile(ColorProfileInfo.strSerialNumber);
		}
	}
}
