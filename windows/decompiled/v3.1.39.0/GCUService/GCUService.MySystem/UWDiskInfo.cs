using System;
using System.Runtime.InteropServices;

namespace GCUService.MySystem;

public class UWDiskInfo
{
	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct DISK_INFO
	{
		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
		public string Model;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
		public string FirmwareRev;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
		public string Interface;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
		public string SerialNumber;

		[MarshalAs(UnmanagedType.U4)]
		public uint DiskSize;

		[MarshalAs(UnmanagedType.I4)]
		public int DetectedPowerOnHours;

		[MarshalAs(UnmanagedType.U4)]
		public uint PowerOnCount;

		[MarshalAs(UnmanagedType.I4)]
		public int Temperature;

		[MarshalAs(UnmanagedType.Bool)]
		public bool IsSsd;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct DISK_INFO_LIST
	{
		[MarshalAs(UnmanagedType.I4)]
		public int disk_count;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 5)]
		public DISK_INFO[] disk;
	}

	private const int MAX_DISK = 5;

	private REPORT_DISK_INFO_LIST m_report_list;

	private DISK_INFO_LIST m_dll_list;

	private IntPtr m_dll_unmanageddata = IntPtr.Zero;

	[DllImport("UWDiskInfo.dll")]
	private static extern void Init();

	[DllImport("UWDiskInfo.dll")]
	private static extern bool QueryDiskInfo(IntPtr disk_list);

	public UWDiskInfo()
	{
		m_dll_list = default(DISK_INFO_LIST);
		m_dll_list.disk_count = 0;
		m_dll_list.disk = new DISK_INFO[5];
		m_dll_unmanageddata = Marshal.AllocHGlobal(Marshal.SizeOf(m_dll_list));
		m_report_list = new REPORT_DISK_INFO_LIST();
		m_report_list.disk = new REPORT_DISK_INFO[5];
		m_report_list.size_info = new DISK_SIZE_INFO[5];
		Init();
	}

	public REPORT_DISK_INFO_LIST GetDiskInfo()
	{
		if (QueryDiskInfo(m_dll_unmanageddata))
		{
			m_dll_list = (DISK_INFO_LIST)Marshal.PtrToStructure(m_dll_unmanageddata, typeof(DISK_INFO_LIST));
		}
		m_report_list.count = m_dll_list.disk_count;
		for (uint num = 0u; num < m_dll_list.disk_count; num++)
		{
			m_report_list.disk[num].Model = m_dll_list.disk[num].Model;
			m_report_list.disk[num].Interface = m_dll_list.disk[num].Interface;
			m_report_list.disk[num].Temperature = m_dll_list.disk[num].Temperature.ToString();
			m_report_list.disk[num].DiskType = (m_dll_list.disk[num].IsSsd ? "SSD" : "HDD");
			m_report_list.disk[num].PowerOnCount = m_dll_list.disk[num].PowerOnCount.ToString();
			m_report_list.disk[num].PowerOnHours = m_dll_list.disk[num].DetectedPowerOnHours.ToString();
		}
		return m_report_list;
	}
}
