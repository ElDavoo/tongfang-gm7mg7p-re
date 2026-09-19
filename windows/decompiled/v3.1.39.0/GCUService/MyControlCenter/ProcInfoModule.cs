using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Management;
using System.Runtime.InteropServices;
using System.Security.Principal;

namespace MyControlCenter;

public class ProcInfoModule
{
	private enum TOKEN_INFORMATION_CLASS
	{
		TokenUser = 1
	}

	private struct TOKEN_USER
	{
		public _SID_AND_ATTRIBUTES User;
	}

	public struct _SID_AND_ATTRIBUTES
	{
		public IntPtr Sid;

		public int Attributes;
	}

	public const int TOKEN_QUERY = 8;

	public static List<ProcInfoDto> QueryProcesses()
	{
		Stopwatch stopwatch = new Stopwatch();
		stopwatch.Start();
		Dictionary<int, ProcInfoDto> procs = QueryProcInfoByCIMV2();
		stopwatch.Stop();
		Console.WriteLine($"QueryProcInfoByCIMV2 {stopwatch.ElapsedMilliseconds:n0}ms");
		stopwatch.Restart();
		Process.GetProcesses().AsParallel().ForAll(delegate(Process o)
		{
			try
			{
				if (procs.ContainsKey(o.Id))
				{
					procs[o.Id].UserName = ExGetProcUserByHandle(o.Handle);
				}
			}
			catch
			{
			}
		});
		stopwatch.Stop();
		Console.WriteLine($"Get Proc Owner {stopwatch.ElapsedMilliseconds:n0}ms");
		return procs.Values.OrderBy((ProcInfoDto o) => o.Name).ToList();
	}

	[DllImport("advapi32")]
	private static extern bool OpenProcessToken(IntPtr ProcessHandle, int DesiredAccess, ref IntPtr TokenHandle);

	[DllImport("advapi32", CharSet = CharSet.Auto)]
	private static extern bool GetTokenInformation(IntPtr hToken, TOKEN_INFORMATION_CLASS tokenInfoClass, IntPtr TokenInformation, int tokeInfoLength, ref int reqLength);

	[DllImport("kernel32")]
	private static extern bool CloseHandle(IntPtr handle);

	public static bool DumpUserInfo(IntPtr pToken, out IntPtr SID)
	{
		int desiredAccess = 8;
		IntPtr TokenHandle = IntPtr.Zero;
		bool result = false;
		SID = IntPtr.Zero;
		try
		{
			if (OpenProcessToken(pToken, desiredAccess, ref TokenHandle))
			{
				result = ProcessTokenToSid(TokenHandle, out SID);
				CloseHandle(TokenHandle);
			}
			return result;
		}
		catch (Exception)
		{
			return false;
		}
	}

	private static bool ProcessTokenToSid(IntPtr token, out IntPtr SID)
	{
		IntPtr intPtr = Marshal.AllocHGlobal(256);
		SID = IntPtr.Zero;
		try
		{
			int reqLength = 256;
			bool tokenInformation = GetTokenInformation(token, TOKEN_INFORMATION_CLASS.TokenUser, intPtr, reqLength, ref reqLength);
			if (tokenInformation)
			{
				SID = ((TOKEN_USER)Marshal.PtrToStructure(intPtr, typeof(TOKEN_USER))).User.Sid;
			}
			return tokenInformation;
		}
		catch (Exception)
		{
			return false;
		}
		finally
		{
			Marshal.FreeHGlobal(intPtr);
		}
	}

	public static string ExGetProcUserByHandle(IntPtr handle)
	{
		try
		{
			IntPtr SID = IntPtr.Zero;
			if (DumpUserInfo(handle, out SID))
			{
				return new SecurityIdentifier(SID).Translate(typeof(NTAccount)).Value;
			}
		}
		catch
		{
		}
		return "Unknown";
	}

	public static Dictionary<int, ProcInfoDto> QueryProcInfoByCIMV2()
	{
		return (from o in new ManagementObjectSearcher("root\\CIMV2", "SELECT * FROM Win32_PerfFormattedData_PerfProc_Process").Get().Cast<ManagementObject>().ToList()
				.Select(delegate(ManagementObject queryObj)
				{
					int num = Convert.ToInt32(queryObj["IDProcess"]);
					return (num == 0) ? null : new ProcInfoDto
					{
						ProcessId = num,
						Name = queryObj["Name"].ToString(),
						PrivWorkSet = string.Format("{0:n0}K", Convert.ToUInt64(queryObj["WorkingSetPrivate"]) / 1024),
						ProcTimeInPerc = string.Format("{0:n0}%", Convert.ToInt64(queryObj["PercentProcessorTime"]))
					};
				})
			where o != null
			select o).ToDictionary((ProcInfoDto o) => o.ProcessId, (ProcInfoDto o) => o);
	}
}
