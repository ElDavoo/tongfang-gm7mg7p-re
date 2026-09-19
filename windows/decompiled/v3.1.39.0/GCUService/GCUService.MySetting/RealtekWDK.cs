using System;
using System.Collections.Generic;
using System.Linq;
using System.Timers;
using Microsoft.Win32;
using Utility;

namespace GCUService.MySetting;

internal class RealtekWDK
{
	private static readonly RealtekWDK model = new RealtekWDK();

	private List<string> RealtekValueList = new List<string> { "RSA0_R0_L", "RSA0_R0_L_ohmX10", "RSA0_R0_R", "RSA0_R0_R_ohmX10" };

	private Timer realtekCalTimer;

	private int clearValue = 1;

	public static RealtekWDK Instance => model;

	private RealtekWDK()
	{
		clearValue = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "SpeakerCalibrationClear", 1);
		realtekCalTimer = new Timer();
		realtekCalTimer.Interval = 60000.0;
		realtekCalTimer.Elapsed += RealtekCalTimer_Elapsed;
	}

	public int GetClearValue()
	{
		return clearValue;
	}

	public void SetclearValue(int value)
	{
		clearValue = value;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "SpeakerCalibrationClear", value, RegistryValueKind.DWord);
	}

	public bool AuditMode()
	{
		if ((string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\Microsoft\\Windows\\CurrentVersion\\Setup\\State", "ImageState", "") == "IMAGE_STATE_COMPLETE")
		{
			return false;
		}
		return true;
	}

	public void StartCalibration()
	{
		realtekCalTimer.Start();
	}

	private void RealtekCalTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		if (RealtekRegValid())
		{
			float rangleL = LoadRangeL();
			float rangleR = LoadRangeR();
			SpeakerCalibration("RSA0_R0_L", "L", rangleL, rangleR);
			SpeakerCalibration("RSA0_R0_R", "R", rangleL, rangleR);
			realtekCalTimer.Stop();
		}
	}

	private bool RealtekRegValid()
	{
		try
		{
			foreach (string realtekValue in RealtekValueList)
			{
				if (Convert.ToUInt32(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\Realtek\\SpkProtection", realtekValue, uint.MaxValue)) == uint.MaxValue)
				{
					return false;
				}
			}
			return true;
		}
		catch
		{
			return false;
		}
	}

	private float LoadRangeL()
	{
		return Convert.ToSingle(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "SpeakerCalibrationRangeL", "3.4"));
	}

	private float LoadRangeR()
	{
		return Convert.ToSingle(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "SpeakerCalibrationRangeR", "4.6"));
	}

	private void SpeakerCalibration(string TargetName, string biosString, float rangleL = 3.4f, float rangleR = 4.6f)
	{
		try
		{
			bool flag = false;
			bool flag2 = true;
			object value = RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\Realtek\\SpkProtection", TargetName, 0);
			float num = (float)ConvertToOhm(Convert.ToUInt32(value));
			if (num < rangleL || num > rangleR)
			{
				flag = true;
			}
			if (!flag)
			{
				return;
			}
			new SMBIOSFirmwareTable();
			string[] array = new string[2];
			array = SMBIOSFirmwareTable.GetString(11u, 19u).Split('_');
			uint num2 = 0u;
			uint num3 = 0u;
			if (array.Count() > 1)
			{
				num2 = Convert.ToUInt32(array[0].Trim(), 16);
				num3 = Convert.ToUInt32(array[1].Trim(), 16);
				float num4 = (float)ConvertToOhm(Convert.ToUInt32(num2));
				float num5 = (float)ConvertToOhm(Convert.ToUInt32(num3));
				if (biosString == "L" && num4 == 0f)
				{
					flag2 = false;
				}
				if (biosString == "R" && num5 == 0f)
				{
					flag2 = false;
				}
			}
			else
			{
				flag2 = false;
			}
			if (flag2)
			{
				if (biosString == "L")
				{
					RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\Realtek\\SpkProtection", TargetName, num2, RegistryValueKind.DWord);
					LogCtrl.Write(TargetName + "Spker Calibration successful !");
				}
				else if (biosString == "R")
				{
					RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\Realtek\\SpkProtection", TargetName, num3, RegistryValueKind.DWord);
					LogCtrl.Write(TargetName + "Spker Calibration successful !");
				}
				else
				{
					LogCtrl.Write("Spker Calibration fail !");
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Spker Calibration Error : " + ex.ToString());
		}
	}

	private double ConvertToOhm(uint value)
	{
		double result = 0.0;
		if (value != 0)
		{
			result = Math.Round(Convert.ToDouble(16777216f / (float)value), 3);
		}
		return result;
	}

	public void ClearRealtekReg()
	{
		try
		{
			foreach (string realtekValue in RealtekValueList)
			{
				RegistryCtrl.RegistrySoftwareKeyDelete(RegistryHive.LocalMachine, "\\Realtek\\SpkProtection", realtekValue);
			}
		}
		catch (Exception)
		{
		}
	}
}
