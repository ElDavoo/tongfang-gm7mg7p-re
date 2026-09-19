using System;
using System.Runtime.InteropServices;
using Utility;

namespace UsbHidModel;

internal class HIDManager : HIDNativeMethods
{
	public IntPtr m_Handle;

	public int m_FeatureSize;

	public ushort m_UsagePage;

	private static string GetDevicePath(IntPtr hInfoSet, ref DeviceInterfaceData oInterface)
	{
		uint nRequiredSize = 0u;
		if (!HIDNativeMethods.SetupDiGetDeviceInterfaceDetail(hInfoSet, ref oInterface, IntPtr.Zero, 0u, ref nRequiredSize, IntPtr.Zero))
		{
			LogCtrl.Write("HID_Manager|GetDevicePath : SetupDiGetDeviceInterfaceDetail failed");
		}
		DeviceInterfaceDetailData oDetailData = new DeviceInterfaceDetailData
		{
			Size = ((Marshal.SizeOf(typeof(IntPtr)) == 8) ? 8 : 5)
		};
		if (!HIDNativeMethods.SetupDiGetDeviceInterfaceDetail(hInfoSet, ref oInterface, ref oDetailData, nRequiredSize, ref nRequiredSize, IntPtr.Zero))
		{
			LogCtrl.Write("HID_Manager|GetDevicePath : SetupDiGetDeviceInterfaceDetail failed");
		}
		return oDetailData.DevicePath;
	}

	public bool Init(ushort VID, ushort PID, ushort USAGE)
	{
		try
		{
			HIDNativeMethods.HidD_GetHidGuid(out var gHid);
			IntPtr intPtr = HIDNativeMethods.SetupDiGetClassDevs(ref gHid, null, IntPtr.Zero, 18u);
			if (intPtr == HIDNativeMethods.InvalidHandleValue)
			{
				LogCtrl.Write("HID_Manager|Init : SetupDiGetClassDevs failed");
				return false;
			}
			DeviceInterfaceData oInterfaceData = default(DeviceInterfaceData);
			oInterfaceData.Size = Marshal.SizeOf(oInterfaceData);
			int i;
			for (i = 0; HIDNativeMethods.SetupDiEnumDeviceInterfaces(intPtr, 0u, ref gHid, (uint)i, ref oInterfaceData); i++)
			{
				IntPtr intPtr2 = HIDNativeMethods.CreateFile(GetDevicePath(intPtr, ref oInterfaceData), 3221225472u, 3u, IntPtr.Zero, 3u, 1073741824u, IntPtr.Zero);
				if (intPtr2 != HIDNativeMethods.InvalidHandleValue)
				{
					HIDD_ATTRIBUTES attributes = default(HIDD_ATTRIBUTES);
					attributes.Size = (uint)Marshal.SizeOf(attributes);
					if (!HIDNativeMethods.HidD_GetAttributes(intPtr2, ref attributes))
					{
						LogCtrl.Write("HID_Manager|Init : HidD_GetAttributes failed");
					}
					LogCtrl.Write($"HID_Manager|Init : PID ={attributes.ProductID} VID={attributes.VendorID}");
					if (attributes.ProductID == PID && attributes.VendorID == VID && HIDNativeMethods.HidD_GetPreparsedData(intPtr2, out var lpData))
					{
						if (HIDNativeMethods.HidP_GetCaps(lpData, out var oCaps) != 1114112)
						{
							LogCtrl.Write("HID_Manager|Init HidP_GetCaps failed");
						}
						else
						{
							LogCtrl.Write($"HID_Manager|Init :  usageid={oCaps.Usage:x} usagepage={oCaps.UsagePage:x} InputReportLen={oCaps.InputReportByteLength} OutputReportLen={oCaps.OutputReportByteLength} FeatureReportLen{oCaps.FeatureReportByteLength}");
							if (oCaps.Usage == USAGE)
							{
								m_Handle = intPtr2;
								m_UsagePage = oCaps.UsagePage;
								m_FeatureSize = oCaps.FeatureReportByteLength;
								if (!HIDNativeMethods.SetupDiDestroyDeviceInfoList(intPtr))
								{
									Log.s(LOG_LEVEL.ERROR, "HID_Manager|Init : SetupDiDestroyDeviceInfoList failed ");
								}
								LogCtrl.Write("********************************** Init HID Device successful !*******************************");
								return true;
							}
						}
					}
				}
				HIDNativeMethods.CloseHandle(intPtr2);
			}
			if (!HIDNativeMethods.SetupDiDestroyDeviceInfoList(intPtr))
			{
				LogCtrl.Write("HID_Manager|Init : SetupDiDestroyDeviceInfoList failed ");
			}
			LogCtrl.Write($"HID_Manager|Init :  Find HID Device Interface = {i}");
			return false;
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"HID_Manager|Init : Failed {ex.ToString()}");
			return false;
		}
	}

	public void Deinit()
	{
		if (m_Handle != IntPtr.Zero)
		{
			HIDNativeMethods.CloseHandle(m_Handle);
		}
	}

	public ushort GetUsagePage()
	{
		return m_UsagePage;
	}

	public bool WriteFeature(byte[] buffer)
	{
		return HIDNativeMethods.HidD_SetFeature(m_Handle, buffer, m_FeatureSize);
	}

	public bool GetFeature(byte[] buffer)
	{
		return HIDNativeMethods.HidD_GetFeature(m_Handle, buffer, m_FeatureSize);
	}
}
