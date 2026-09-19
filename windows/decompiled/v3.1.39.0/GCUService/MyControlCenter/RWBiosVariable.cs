using System;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal class RWBiosVariable
{
	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	internal struct LUID
	{
		internal int LowPart;

		internal uint HighPart;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	internal struct LUID_AND_ATTRIBUTES
	{
		internal LUID Luid;

		internal uint Attributes;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	internal struct TOKEN_PRIVILEGES
	{
		internal int PrivilegeCount;

		internal LUID_AND_ATTRIBUTES Privilege;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	internal struct TokPriv1Luid
	{
		public int Count;

		public long Luid;

		public int Attr;
	}

	internal const int SE_PRIVILEGE_ENABLED = 2;

	internal const int TOKEN_QUERY = 8;

	internal const int TOKEN_ADJUST_PRIVILEGES = 32;

	internal const string SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege";

	[DllImport("advapi32.dll", ExactSpelling = true, SetLastError = true)]
	internal static extern bool AdjustTokenPrivileges(IntPtr htok, bool disall, ref TOKEN_PRIVILEGES newst, int len, IntPtr prev, IntPtr relen);

	[DllImport("kernel32.dll", ExactSpelling = true)]
	internal static extern IntPtr GetCurrentProcess();

	[DllImport("advapi32.dll", ExactSpelling = true, SetLastError = true)]
	internal static extern bool OpenProcessToken(IntPtr h, int acc, ref IntPtr phtok);

	[DllImport("advapi32.dll", SetLastError = true)]
	internal static extern bool LookupPrivilegeValue(string host, string name, ref LUID pluid);

	[DllImport("kernel32.dll", SetLastError = true)]
	private static extern bool SetFirmwareEnvironmentVariable(string lpName, string lpGuid, IntPtr pValue, int nSize);

	[DllImport("kernel32.dll", SetLastError = true)]
	private static extern uint GetFirmwareEnvironmentVariable(string lpName, string lpGuid, IntPtr pBuffer, int nSize);

	public bool RaiseTokenPrivilege()
	{
		IntPtr phtok = IntPtr.Zero;
		if (OpenProcessToken(GetCurrentProcess(), 32, ref phtok))
		{
			LUID pluid = default(LUID);
			LUID pluid2 = default(LUID);
			LUID pluid3 = default(LUID);
			if (LookupPrivilegeValue(null, "SeSystemEnvironmentPrivilege", ref pluid) && LookupPrivilegeValue(null, "SeBackupPrivilege", ref pluid2) && LookupPrivilegeValue(null, "SeRestorePrivilege", ref pluid3))
			{
				TOKEN_PRIVILEGES newst = new TOKEN_PRIVILEGES
				{
					PrivilegeCount = 1,
					Privilege = 
					{
						Attributes = 2u,
						Luid = pluid
					}
				};
				if (AdjustTokenPrivileges(phtok, disall: false, ref newst, 1028, IntPtr.Zero, IntPtr.Zero))
				{
					newst.Privilege.Luid = pluid2;
					if (AdjustTokenPrivileges(phtok, disall: false, ref newst, 1028, IntPtr.Zero, IntPtr.Zero))
					{
						newst.Privilege.Luid = pluid3;
						if (AdjustTokenPrivileges(phtok, disall: false, ref newst, 1028, IntPtr.Zero, IntPtr.Zero))
						{
							return true;
						}
					}
				}
			}
			else
			{
				Console.WriteLine("LookupPrivilegeValue failed");
			}
		}
		return false;
	}

	public RWBiosVariable()
	{
		RaiseTokenPrivilege();
	}

	public void Read(string _guid, string _name, out byte[] data, ref uint size)
	{
		IntPtr intPtr = Marshal.AllocHGlobal(512);
		uint firmwareEnvironmentVariable = GetFirmwareEnvironmentVariable(_name, _guid, intPtr, 512);
		if (firmwareEnvironmentVariable != 0)
		{
			data = new byte[firmwareEnvironmentVariable];
			Marshal.Copy(intPtr, data, 0, data.Length);
			size = firmwareEnvironmentVariable;
		}
		else
		{
			size = 0u;
			data = null;
		}
		Marshal.Release(intPtr);
	}

	public bool Write(string _guid, string _name, byte[] data, int size)
	{
		IntPtr intPtr = Marshal.AllocHGlobal(size);
		Marshal.Copy(data, 0, intPtr, size);
		bool result = SetFirmwareEnvironmentVariable(_name, _guid, intPtr, size);
		Marshal.Release(intPtr);
		return result;
	}
}
