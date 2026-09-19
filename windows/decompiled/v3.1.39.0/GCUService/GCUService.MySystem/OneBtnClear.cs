using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

namespace GCUService.MySystem;

internal class OneBtnClear
{
	private enum RecycleFlags : uint
	{
		SHERB_NOCONFIRMATION = 1u,
		SHERB_NOPROGRESSUI = 1u,
		SHERB_NOSOUND = 4u
	}

	[StructLayout(LayoutKind.Sequential, Pack = 4)]
	public struct SHQUERYRBINFO
	{
		public int cbSize;

		public long i64Size;

		public long i64NumItems;
	}

	private bool isCleanCompleted;

	[DllImport("Shell32.dll", CharSet = CharSet.Unicode)]
	private static extern uint SHEmptyRecycleBin(IntPtr hwnd, string pszRootPath, RecycleFlags dwFlags);

	[DllImport("shell32.dll", CharSet = CharSet.Unicode)]
	private static extern int SHQueryRecycleBin(string pszRootPath, ref SHQUERYRBINFO pSHQueryRBInfo);

	public bool isRecycleBinIsEmpty()
	{
		SHQUERYRBINFO pSHQueryRBInfo = new SHQUERYRBINFO
		{
			cbSize = Marshal.SizeOf(typeof(SHQUERYRBINFO))
		};
		SHQueryRecycleBin(string.Empty, ref pSHQueryRBInfo);
		return (int)pSHQueryRBInfo.i64NumItems == 0;
	}

	public List<string> GetRecycleBinSize()
	{
		SHQUERYRBINFO pSHQueryRBInfo = default(SHQUERYRBINFO);
		List<string> list = new List<string>();
		pSHQueryRBInfo.cbSize = Marshal.SizeOf(typeof(SHQUERYRBINFO));
		try
		{
			if (SHQueryRecycleBin(null, ref pSHQueryRBInfo) == 0)
			{
				list.Add(pSHQueryRBInfo.i64NumItems.ToString());
				list.Add(string.Format("{0}", (Convert.ToDouble(pSHQueryRBInfo.i64Size) / Convert.ToDouble(1024) / Convert.ToDouble(1024)).ToString("#,###.##")));
				return list;
			}
			throw new Win32Exception(Marshal.GetLastWin32Error());
		}
		catch (Exception)
		{
			return null;
		}
	}

	public void systemCleanProcess()
	{
		new Thread((ParameterizedThreadStart)delegate
		{
			try
			{
				GetRecycleBinSize();
				isCleanCompleted = false;
				string folderPath = Environment.GetFolderPath(Environment.SpecialFolder.InternetCache);
				ClearTempData(new DirectoryInfo(folderPath));
				Environment.GetFolderPath(Environment.SpecialFolder.Cookies);
				ClearTempData(new DirectoryInfo(folderPath));
				Environment.GetFolderPath(Environment.SpecialFolder.History);
				ClearTempData(new DirectoryInfo(folderPath));
				ClearTempData(new DirectoryInfo("C:\\Windows\\Temp"));
				ClearTempData(new DirectoryInfo(Path.GetTempPath()));
				SHEmptyRecycleBin(IntPtr.Zero, null, RecycleFlags.SHERB_NOCONFIRMATION);
			}
			catch (Exception)
			{
			}
		}).Start();
	}

	private static void ClearTempData(DirectoryInfo di)
	{
		FileInfo[] files = di.GetFiles();
		foreach (FileInfo fileInfo in files)
		{
			try
			{
				fileInfo.Delete();
				Console.WriteLine(fileInfo.FullName);
			}
			catch (Exception arg)
			{
				Console.WriteLine("{0}", arg);
			}
		}
		DirectoryInfo[] directories = di.GetDirectories();
		foreach (DirectoryInfo directoryInfo in directories)
		{
			try
			{
				directoryInfo.Delete(recursive: true);
				Console.WriteLine(directoryInfo.FullName);
			}
			catch (Exception arg2)
			{
				Console.WriteLine("{0}", arg2);
			}
		}
	}
}
