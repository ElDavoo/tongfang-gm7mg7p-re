using System;
using System.IO;
using System.Runtime.InteropServices;

namespace BatteryModel;

internal static class BatteryInfo
{
	internal static BatteryInformation GetInformation()
	{
		IntPtr hglobal = IntPtr.Zero;
		IntPtr intPtr = IntPtr.Zero;
		IntPtr intPtr2 = IntPtr.Zero;
		IntPtr intPtr3 = IntPtr.Zero;
		IntPtr intPtr4 = IntPtr.Zero;
		try
		{
			Guid guid = Win32.GUID_DEVCLASS_BATTERY;
			IntPtr intPtr5 = Win32.SetupDiGetClassDevs(ref guid, null, IntPtr.Zero, Win32.DEVICE_GET_CLASS_FLAGS.DIGCF_PRESENT | Win32.DEVICE_GET_CLASS_FLAGS.DIGCF_DEVICEINTERFACE);
			Win32.SP_DEVICE_INTERFACE_DATA devInterfaceData = default(Win32.SP_DEVICE_INTERFACE_DATA);
			devInterfaceData.CbSize = Marshal.SizeOf(devInterfaceData);
			Guid guid2 = Win32.GUID_DEVCLASS_BATTERY;
			Win32.SetupDiEnumDeviceInterfaces(intPtr5, IntPtr.Zero, ref guid2, 0u, ref devInterfaceData);
			hglobal = Marshal.AllocHGlobal(120);
			Win32.SP_DEVICE_INTERFACE_DETAIL_DATA deviceInterfaceDetailData = new Win32.SP_DEVICE_INTERFACE_DETAIL_DATA
			{
				CbSize = ((IntPtr.Size == 8) ? 8 : (4 + Marshal.SystemDefaultCharSize))
			};
			Win32.SetupDiGetDeviceInterfaceDetail(intPtr5, ref devInterfaceData, ref deviceInterfaceDetailData, 120u, out var _, IntPtr.Zero);
			IntPtr handle = Win32.CreateFile(deviceInterfaceDetailData.DevicePath, FileAccess.ReadWrite, FileShare.ReadWrite, IntPtr.Zero, FileMode.Open, Win32.FILE_ATTRIBUTES.Normal, IntPtr.Zero);
			Win32.BATTERY_QUERY_INFORMATION structure = default(Win32.BATTERY_QUERY_INFORMATION);
			uint inBuffer = 0u;
			Win32.DeviceIoControl(handle, 2703424u, ref inBuffer, 0u, ref structure.BatteryTag, (uint)Marshal.SizeOf(structure.BatteryTag), out var bytesReturned, IntPtr.Zero);
			structure.InformationLevel = Win32.BATTERY_QUERY_INFORMATION_LEVEL.BatteryInformation;
			int num = Marshal.SizeOf(structure);
			int num2 = Marshal.SizeOf(default(Win32.BATTERY_INFORMATION));
			intPtr = Marshal.AllocHGlobal(num);
			Marshal.StructureToPtr(structure, intPtr, fDeleteOld: false);
			intPtr2 = Marshal.AllocHGlobal(num2);
			Marshal.StructureToPtr(default(Win32.BATTERY_INFORMATION), intPtr2, fDeleteOld: false);
			Win32.DeviceIoControl(handle, 2703428u, intPtr, (uint)num, intPtr2, (uint)num2, out bytesReturned, IntPtr.Zero);
			Win32.BATTERY_INFORMATION bATTERY_INFORMATION = (Win32.BATTERY_INFORMATION)Marshal.PtrToStructure(intPtr2, typeof(Win32.BATTERY_INFORMATION));
			Win32.BATTERY_WAIT_STATUS structure2 = new Win32.BATTERY_WAIT_STATUS
			{
				BatteryTag = structure.BatteryTag
			};
			int num3 = Marshal.SizeOf(structure2);
			int num4 = Marshal.SizeOf(default(Win32.BATTERY_STATUS));
			intPtr3 = Marshal.AllocHGlobal(num3);
			Marshal.StructureToPtr(structure2, intPtr3, fDeleteOld: false);
			intPtr4 = Marshal.AllocHGlobal(num4);
			Marshal.StructureToPtr(default(Win32.BATTERY_STATUS), intPtr4, fDeleteOld: false);
			Win32.DeviceIoControl(handle, 2703436u, intPtr3, (uint)num3, intPtr4, (uint)num4, out bytesReturned, IntPtr.Zero);
			Win32.BATTERY_STATUS bATTERY_STATUS = (Win32.BATTERY_STATUS)Marshal.PtrToStructure(intPtr4, typeof(Win32.BATTERY_STATUS));
			Win32.SetupDiDestroyDeviceInfoList(intPtr5);
			return new BatteryInformation
			{
				DesignedMaxCapacity = bATTERY_INFORMATION.DesignedCapacity,
				FullChargeCapacity = bATTERY_INFORMATION.FullChargedCapacity,
				CurrentCapacity = bATTERY_STATUS.Capacity,
				Voltage = bATTERY_STATUS.Voltage,
				DischargeRate = bATTERY_STATUS.Rate
			};
		}
		finally
		{
			Marshal.FreeHGlobal(hglobal);
			Marshal.FreeHGlobal(intPtr);
			Marshal.FreeHGlobal(intPtr2);
			Marshal.FreeHGlobal(intPtr4);
			Marshal.FreeHGlobal(intPtr3);
		}
	}

	private static bool DeviceIoControl(IntPtr deviceHandle, uint controlCode, ref uint output)
	{
		uint inBuffer = 0u;
		uint bytesReturned;
		bool num = Win32.DeviceIoControl(deviceHandle, controlCode, ref inBuffer, 0u, ref output, (uint)Marshal.SizeOf(output), out bytesReturned, IntPtr.Zero);
		if (!num)
		{
			int lastWin32Error = Marshal.GetLastWin32Error();
			if (lastWin32Error != 0)
			{
				throw Marshal.GetExceptionForHR(lastWin32Error);
			}
			throw new Exception("DeviceIoControl call failed but Win32 didn't catch an error.");
		}
		return num;
	}

	private static bool DeviceIoControl(IntPtr deviceHandle, uint controlCode, IntPtr input, int inputSize, IntPtr output, int outputSize)
	{
		uint bytesReturned;
		bool num = Win32.DeviceIoControl(deviceHandle, controlCode, input, (uint)inputSize, output, (uint)outputSize, out bytesReturned, IntPtr.Zero);
		if (!num)
		{
			int lastWin32Error = Marshal.GetLastWin32Error();
			if (lastWin32Error != 0)
			{
				throw Marshal.GetExceptionForHR(lastWin32Error);
			}
			throw new Exception("DeviceIoControl call failed but Win32 didn't catch an error.");
		}
		return num;
	}

	private static IntPtr SetupDiGetClassDevs(Guid guid, Win32.DEVICE_GET_CLASS_FLAGS flags)
	{
		IntPtr intPtr = Win32.SetupDiGetClassDevs(ref guid, null, IntPtr.Zero, flags);
		if (intPtr == IntPtr.Zero)
		{
			int lastWin32Error = Marshal.GetLastWin32Error();
			if (lastWin32Error != 0)
			{
				throw Marshal.GetExceptionForHR(lastWin32Error);
			}
			throw new Exception("SetupDiGetClassDev call returned a bad handle.");
		}
		return intPtr;
	}
}
