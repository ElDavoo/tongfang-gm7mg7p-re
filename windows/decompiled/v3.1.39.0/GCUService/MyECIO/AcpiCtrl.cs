using System;
using System.Diagnostics;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32;
using Utility;

namespace MyECIO;

public class AcpiCtrl
{
	private static readonly AcpiCtrl AcpiModel = new AcpiCtrl();

	public const uint GENERIC_READ = 2147483648u;

	public const uint GENERIC_WRITE = 1073741824u;

	public const uint FILE_SHARE_WRITE = 2u;

	public const uint FILE_SHARE_READ = 1u;

	public const uint FILE_FLAG_OVERLAPPED = 1073741824u;

	public const uint OPEN_EXISTING = 3u;

	public const uint OPEN_ALWAYS = 4u;

	public const uint METHOD_BUFFERED = 0u;

	public const uint METHOD_IN_DIRECT = 1u;

	public const uint METHOD_OUT_DIRECT = 2u;

	public const uint METHOD_NEITHER = 3u;

	public const uint FILE_READ_ACCESS = 1u;

	public const uint FILE_WRITE_ACCESS = 2u;

	public const uint GPD_TYPE = 40000u;

	public const byte SMRW_CMD_READ = 187;

	public const byte SMRW_CMD_WRITE = 170;

	public const uint IOCTL_GPD_READ_PORT_UCHAR = 2621465600u;

	public const uint IOCTL_GPD_READ_PORT_USHORT = 2621465604u;

	public const uint IOCTL_GPD_READ_PORT_ULONG = 2621465608u;

	public const uint IOCTL_GPD_WRITE_PORT_UCHAR = 2621482048u;

	public const uint IOCTL_GPD_WRITE_PORT_USHORT = 2621482052u;

	public const uint IOCTL_GPD_WRITE_PORT_ULONG = 2621482056u;

	public const uint IOCTL_GPD_ACPI_CMREAD = 2621482112u;

	public const uint IOCTL_GPD_ACPI_CMWRITE = 2621482116u;

	public const uint IOCTL_GPD_ACPI_ECREAD = 2621482120u;

	public const uint IOCTL_GPD_ACPI_ECWRITE = 2621482124u;

	public const uint IOCTL_GPD_ACPI_MMREADB = 2621482128u;

	public const uint IOCTL_GPD_ACPI_MMREADD = 2621482132u;

	public const uint IOCTL_GPD_ACPI_MMWRITEB = 2621482136u;

	public const uint IOCTL_GPD_ACPI_MMWRITED = 2621482140u;

	public const uint IOCTL_GPD_ACPI_PEREAD = 2621482144u;

	public const uint IOCTL_GPD_ACPI_PEWRITE = 2621482148u;

	public const uint IOCTL_GPD_ACPI_IOREAD = 2621482176u;

	public const uint IOCTL_GPD_ACPI_IOWRITE = 2621482180u;

	public const uint IOCTL_GPD_ACPI_INIOREAD = 2621482184u;

	public const uint IOCTL_GPD_ACPI_INIOWRITE = 2621482188u;

	public const uint IOCTL_GPD_ACPI_TMPREAD1 = 2621482192u;

	public const uint IOCTL_GPD_ACPI_TMPREAD2 = 2621482196u;

	public const uint IOCTL_GPD_ACPI_TMPREAD3 = 2621482200u;

	public const uint IOCTL_GPD_ACPI_TMPWRITE1 = 2621482204u;

	public const uint IOCTL_GPD_ACPI_TMPWRITE2 = 2621482208u;

	public const uint IOCTL_GPD_ACPI_TMPWRITE3 = 2621482212u;

	public const uint IOCTL_GPD_ACPI_SMAPCTABLE = 2621482240u;

	private Stopwatch sw = new Stopwatch();

	private int EC_TimeOut = 2000;

	private static object m_lock_ec = new object();

	private int DelayTime = 10;

	private int errorCount;

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	public static AcpiCtrl Instance => AcpiModel;

	[DllImport("kernel32.dll", SetLastError = true)]
	public static extern IntPtr CreateFile([MarshalAs(UnmanagedType.LPStr)] string strName, uint nAccess, uint nShareMode, IntPtr lpSecurity, uint nCreationFlags, uint nAttributes, IntPtr lpTemplate);

	[DllImport("kernel32.dll", SetLastError = true)]
	public static extern bool CloseHandle(IntPtr hObject);

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	public static extern bool DeviceIoControl(IntPtr handle, uint controlCode, IntPtr inBuffer, int inBufferSize, ref int outBuffer, int outBufferSize, out int bytesReturned, IntPtr overlapped);

	[DllImport("Kernel32.dll", SetLastError = true)]
	public static extern bool DeviceIoControl(IntPtr handle, uint controlCode, IntPtr inBuffer, int inBufferSize, byte[] OutBuffer, int outBufferSize, out int bytesReturned, IntPtr overlapped);

	[DllImport("ACPIDriverDll.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern IntPtr SMAPCTable(IntPtr arg0);

	public AcpiCtrl()
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "ServiceReady", 0, RegistryValueKind.DWord);
		while (!CheckAcpiDriverDeviceExists() && errorCount < 30)
		{
			Thread.Sleep(1000);
			errorCount++;
		}
		if (errorCount < 30)
		{
			LogCtrl.TraceMessage("ACPIDriverInit Ready !", ".ctor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 95);
			try
			{
				EventLog.WriteEntry("GCUService", "ACPIDriver Init Ready !");
				return;
			}
			catch
			{
				return;
			}
		}
		LogCtrl.TraceMessage("ACPIDriverInit Fail !", ".ctor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 106);
		try
		{
			EventLog.WriteEntry("GCUService", "ACPIDriver Init Fail !");
		}
		catch
		{
		}
	}

	public bool CheckAcpiDriverDeviceExists()
	{
		bool result = false;
		foreach (ManagementObject item in new ManagementObjectSearcher("SELECT * FROM Win32_PnPSignedDriver").Get())
		{
			try
			{
				object propertyValue = item.GetPropertyValue("DeviceName");
				if (propertyValue != null && (string.IsNullOrEmpty(propertyValue.ToString()) ? string.Empty : propertyValue.ToString()) == "ACPIDriver")
				{
					result = true;
					return result;
				}
			}
			catch (Exception)
			{
			}
		}
		return result;
	}

	public void Read(string ReadName, ushort Addr, ref byte Data)
	{
		sw.Reset();
		sw.Start();
		if (Monitor.TryEnter(m_lock_ec, EC_TimeOut))
		{
			try
			{
				ReadACPI(2621482120u, Addr, ref Data);
				Thread.Sleep(DelayTime);
			}
			catch (Exception)
			{
			}
			finally
			{
				Monitor.Exit(m_lock_ec);
			}
		}
		sw.Stop();
	}

	public void Write(string ReadName, ushort Addr, byte Data)
	{
		sw.Reset();
		sw.Start();
		if (Monitor.TryEnter(m_lock_ec, EC_TimeOut))
		{
			try
			{
				WriteACPI(2621482124u, Addr, Data);
				Thread.Sleep(DelayTime);
			}
			catch (Exception)
			{
			}
			finally
			{
				Monitor.Exit(m_lock_ec);
			}
		}
		sw.Stop();
	}

	public void ReadPciDword(byte Bus, byte Dev, byte Func, uint Offset, ref uint pData)
	{
		sw.Reset();
		sw.Start();
		if (Monitor.TryEnter(m_lock_ec, EC_TimeOut))
		{
			try
			{
				int data = 0;
				int addr = 0;
				ReadACPI(2621482144u, addr, ref data);
				pData = Convert.ToUInt32(data);
			}
			catch (Exception)
			{
			}
			finally
			{
				Monitor.Exit(m_lock_ec);
			}
		}
		sw.Stop();
	}

	public void ReadSmartApcTableByKey(byte Offset, ref byte[] pData)
	{
		sw.Reset();
		sw.Start();
		if (Monitor.TryEnter(m_lock_ec, EC_TimeOut))
		{
			try
			{
				IntPtr intPtr = CreateFile("\\\\.\\ACPIDriver", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
				if (intPtr != IntPtr.Zero)
				{
					byte[] source = new byte[2] { 187, Offset };
					int num = 2;
					IntPtr intPtr2 = Marshal.AllocHGlobal(num);
					Marshal.Copy(source, 0, intPtr2, 2);
					byte[] array = new byte[4] { 255, 255, 255, 255 };
					int outBufferSize = 4;
					if (!DeviceIoControl(intPtr, 2621482240u, intPtr2, num, array, outBufferSize, out var _, IntPtr.Zero))
					{
						LogCtrl.TraceMessage("DeviceIoControl fail.", "ReadSmartApcTableByKey", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 259);
					}
					pData = array;
					Marshal.FreeHGlobal(intPtr2);
					CloseHandle(intPtr);
				}
				Thread.Sleep(DelayTime);
			}
			catch (Exception ex)
			{
				LogCtrl.TraceMessage("Exception: " + ex.ToString(), "ReadSmartApcTableByKey", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 276);
			}
			finally
			{
				Monitor.Exit(m_lock_ec);
			}
		}
		string text = "";
		byte[] array2 = pData;
		foreach (byte b in array2)
		{
			text = text + b + ",";
		}
		sw.Stop();
		LogCtrl.Write("ReadSmartApcTable " + Offset + " " + text);
	}

	public void WriteSmartApcTableByKey(byte[] Data)
	{
		try
		{
			IntPtr intPtr = CreateFile("\\\\.\\ACPIDriver", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
			if (intPtr != IntPtr.Zero)
			{
				byte[] array = UtilityExtensions.Combine(new byte[1] { 170 }, Data);
				int num = array.Length;
				IntPtr intPtr2 = Marshal.AllocHGlobal(num);
				Marshal.Copy(array, 0, intPtr2, array.Length);
				byte[] outBuffer = new byte[4] { 255, 255, 255, 255 };
				int outBufferSize = 4;
				if (!DeviceIoControl(intPtr, 2621482240u, intPtr2, num, outBuffer, outBufferSize, out var _, IntPtr.Zero))
				{
					LogCtrl.TraceMessage("DeviceIoControl fail.", "WriteSmartApcTableByKey", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 318);
				}
				Marshal.FreeHGlobal(intPtr2);
				CloseHandle(intPtr);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.ToString(), "WriteSmartApcTableByKey", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 327);
		}
	}

	private void ReadACPI(uint ioctrl, int addr, ref int data)
	{
		try
		{
			IntPtr intPtr = CreateFile("\\\\.\\ACPIDriver", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
			if (intPtr != IntPtr.Zero)
			{
				int[] source = new int[1] { addr };
				int num = 4;
				IntPtr intPtr2 = Marshal.AllocHGlobal(num);
				Marshal.Copy(source, 0, intPtr2, 1);
				int outBuffer = 0;
				int outBufferSize = 4;
				DeviceIoControl(intPtr, ioctrl, intPtr2, num, ref outBuffer, outBufferSize, out var _, IntPtr.Zero);
				data = Convert.ToInt32(outBuffer & 0xFFFF);
				Marshal.FreeHGlobal(intPtr2);
				CloseHandle(intPtr);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("[ReadACPI] Exception: " + ex.ToString());
		}
	}

	private void ReadACPI(uint ioctrl, int addr, ref byte data)
	{
		try
		{
			IntPtr intPtr = CreateFile("\\\\.\\ACPIDriver", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
			if (intPtr != IntPtr.Zero)
			{
				int[] source = new int[1] { addr };
				int num = 4;
				IntPtr intPtr2 = Marshal.AllocHGlobal(num);
				Marshal.Copy(source, 0, intPtr2, 1);
				int outBuffer = 0;
				int outBufferSize = 4;
				DeviceIoControl(intPtr, ioctrl, intPtr2, num, ref outBuffer, outBufferSize, out var _, IntPtr.Zero);
				data = Convert.ToByte(outBuffer & 0xFF);
				Marshal.FreeHGlobal(intPtr2);
				CloseHandle(intPtr);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("[ReadACPI] Exception: " + ex.ToString());
		}
	}

	private void WriteACPI(uint ioctrl, int addr, int data)
	{
		IntPtr intPtr = CreateFile("\\\\.\\ACPIDriver", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
		if (intPtr != IntPtr.Zero)
		{
			int[] source = new int[2] { addr, data };
			int num = 8;
			IntPtr intPtr2 = Marshal.AllocHGlobal(num);
			Marshal.Copy(source, 0, intPtr2, 2);
			int outBuffer = 0;
			int outBufferSize = 4;
			DeviceIoControl(intPtr, ioctrl, intPtr2, num, ref outBuffer, outBufferSize, out var _, IntPtr.Zero);
			Marshal.FreeHGlobal(intPtr2);
			CloseHandle(intPtr);
		}
	}

	public void ReadSmartApcTableByDll(byte Offset, ref byte[] pData)
	{
		sw.Reset();
		sw.Start();
		if (Monitor.TryEnter(m_lock_ec, EC_TimeOut))
		{
			try
			{
				byte[] source = new byte[2] { 187, Offset };
				IntPtr intPtr = Marshal.AllocHGlobal(2);
				Marshal.Copy(source, 0, intPtr, 2);
				byte[] array = new byte[4] { 255, 255, 255, 255 };
				Marshal.AllocHGlobal(4);
				Marshal.Copy(SMAPCTable(intPtr), array, 0, 4);
				pData = array;
			}
			catch (Exception ex)
			{
				LogCtrl.TraceMessage("Exception: " + ex.ToString(), "ReadSmartApcTableByDll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 449);
			}
			finally
			{
				Monitor.Exit(m_lock_ec);
			}
		}
		sw.Stop();
		string text = "";
		byte[] array2 = pData;
		foreach (byte b in array2)
		{
			text = text + b + ",";
		}
	}

	public void WriteSmartApcTableByDll(byte[] Data)
	{
		try
		{
			byte[] array = UtilityExtensions.Combine(new byte[1] { 170 }, Data);
			IntPtr intPtr = Marshal.AllocHGlobal(array.Length);
			Marshal.Copy(array, 0, intPtr, array.Length);
			_ = new byte[4] { 255, 255, 255, 255 };
			Marshal.AllocHGlobal(4);
			SMAPCTable(intPtr);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.ToString(), "WriteSmartApcTableByDll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyEC\\AcpiCtrl.cs", 491);
		}
	}
}
