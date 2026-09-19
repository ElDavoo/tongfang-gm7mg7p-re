using System;
using GCUService.MySystem;
using Utility;

namespace MyControlCenter;

internal class DiskInfo
{
	private static string[] SSDInfo1 = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static string[] SSDInfo2 = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static string[] HDDInfo = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static string[] node0 = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static string[] node1 = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static string[] node2 = new string[10] { "null", "null", "null", "null", "null", "null", "null", "null", "null", "null" };

	private static bool SSDFlag = false;

	private UWDiskInfo uWDiskInfo = new UWDiskInfo();

	private static void ConfirmData()
	{
		SSDFlag = false;
		if (node0[8].Equals("1"))
		{
			if (!SSDFlag)
			{
				SSDInfo1 = node0;
				SSDFlag = true;
			}
			else
			{
				SSDInfo2 = node0;
			}
		}
		else if (!node0[8].Equals("null"))
		{
			HDDInfo = node0;
		}
		if (node1[8].Equals("1"))
		{
			if (!SSDFlag)
			{
				SSDInfo1 = node1;
				SSDFlag = true;
			}
			else
			{
				SSDInfo2 = node1;
			}
		}
		else if (!node1[8].Equals("null"))
		{
			HDDInfo = node1;
		}
		if (node2[8].Equals("1"))
		{
			if (!SSDFlag)
			{
				SSDInfo1 = node2;
				SSDFlag = true;
			}
			else
			{
				SSDInfo2 = node2;
			}
		}
		else if (!node2[8].Equals("null"))
		{
			HDDInfo = node2;
		}
	}

	public void UpdateDiskInfo()
	{
		try
		{
			REPORT_DISK_INFO_LIST diskInfo = uWDiskInfo.GetDiskInfo();
			int num = 1;
			REPORT_DISK_INFO[] disk = diskInfo.disk;
			foreach (REPORT_DISK_INFO item in disk)
			{
				ConvertToDiskInfoArray(num, item);
				num++;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Disk info " + ex.ToString());
		}
	}

	private void ConvertToDiskInfoArray(int diskindex, REPORT_DISK_INFO item)
	{
		if (item.DiskType == "SSD" && SSDInfo1[8] != "1")
		{
			SSDInfo1[0] = item.Model;
			SSDInfo1[7] = item.Temperature;
			SSDInfo1[5] = item.PowerOnHours;
			SSDInfo1[6] = item.PowerOnCount;
			SSDInfo1[2] = item.Interface;
			SSDInfo1[9] = item.Usage;
			SSDInfo1[8] = "1";
		}
		else if (item.DiskType == "SSD" && SSDInfo1[8] == "1")
		{
			SSDInfo2[0] = item.Model;
			SSDInfo2[7] = item.Temperature;
			SSDInfo2[5] = item.PowerOnHours;
			SSDInfo2[6] = item.PowerOnCount;
			SSDInfo2[2] = item.Interface;
			SSDInfo2[9] = item.Usage;
			SSDInfo2[8] = "1";
		}
		else if (item.DiskType == "HDD")
		{
			HDDInfo[0] = item.Model;
			HDDInfo[7] = item.Temperature;
			HDDInfo[5] = item.PowerOnHours;
			HDDInfo[6] = item.PowerOnCount;
			HDDInfo[2] = item.Interface;
			HDDInfo[9] = item.Usage;
			HDDInfo[8] = "1";
		}
	}

	public string GetSSD_One_Model()
	{
		return SSDInfo1[0];
	}

	public string GetSSD_One_Temperature()
	{
		return SSDInfo1[7];
	}

	public string GetSSD_One_PowerOnHours()
	{
		return SSDInfo1[5];
	}

	public string GetSSD_One_PowerOnCount()
	{
		return SSDInfo1[6];
	}

	public string GetSSD_One_Interface()
	{
		return SSDInfo1[2];
	}

	public string GetSSD_One_Usage()
	{
		return SSDInfo1[9];
	}

	public string GetSSD_Two_Model()
	{
		return SSDInfo2[0];
	}

	public string GetSSD_Two_Temperature()
	{
		return SSDInfo2[7];
	}

	public string GetSSD_Two_PowerOnHours()
	{
		return SSDInfo2[5];
	}

	public string GetSSD_Two_PowerOnCount()
	{
		return SSDInfo2[6];
	}

	public string GetSSD_Two_Interface()
	{
		return SSDInfo2[2];
	}

	public string GetSSD_Two_Usage()
	{
		return SSDInfo2[9];
	}

	public string GetHDDModel()
	{
		return HDDInfo[0];
	}

	public string GetHDDTemperature()
	{
		return HDDInfo[7];
	}

	public string GetHDDPowerOnHours()
	{
		return HDDInfo[5];
	}

	public string GetHDDPowerOnCount()
	{
		return HDDInfo[6];
	}

	public string GetHDDInterface()
	{
		return HDDInfo[2];
	}

	public string GetHDDUsage()
	{
		return HDDInfo[9];
	}

	public void ResetArray()
	{
		for (int i = 0; i < 10; i++)
		{
			SSDInfo1[i] = "null";
			SSDInfo2[i] = "null";
			HDDInfo[i] = "null";
			node0[i] = "null";
			node1[i] = "null";
			node2[i] = "null";
		}
	}
}
