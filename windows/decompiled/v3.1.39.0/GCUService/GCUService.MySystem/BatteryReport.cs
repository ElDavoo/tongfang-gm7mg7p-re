using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;
using System.Data.SQLite;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using Dapper;

namespace GCUService.MySystem;

internal class BatteryReport
{
	private string path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName;

	private string ReportPath = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\battery-report.html";

	private Dictionary<string, ReportData> OSDailyReport = new Dictionary<string, ReportData>();

	private string dbPath = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\db.sqlite";

	private string cnStr = "data source=" + new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\db.sqlite";

	private const string DBTableName = "BatteryReportData";

	public BatteryReport()
	{
		BatteryReportFromOS();
	}

	public IEnumerable<ReportData> GetBattreyReport()
	{
		//IL_0006: Unknown result type (might be due to invalid IL or missing references)
		//IL_000c: Expected O, but got Unknown
		//IL_0018: Unknown result type (might be due to invalid IL or missing references)
		//IL_001e: Expected O, but got Unknown
		SQLiteConnection val = new SQLiteConnection(cnStr);
		try
		{
			((DbConnection)(object)val).Open();
			string text = "SELECT * FROM BatteryReportData WHERE DTIME <= @now";
			DynamicParameters val2 = new DynamicParameters();
			val2.Add("now", (object)DateTime.Now, (DbType?)DbType.DateTime, (ParameterDirection?)null, (int?)null, (byte?)null, (byte?)null);
			return SqlMapper.Query<ReportData>((IDbConnection)val, text, (object)val2, (IDbTransaction)null, true, (int?)null, (CommandType?)null);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	public int QueryBattreyExaustByDays(int beforedays, int percent)
	{
		//IL_0006: Unknown result type (might be due to invalid IL or missing references)
		//IL_000c: Expected O, but got Unknown
		//IL_003d: Unknown result type (might be due to invalid IL or missing references)
		//IL_0043: Expected O, but got Unknown
		SQLiteConnection val = new SQLiteConnection(cnStr);
		try
		{
			((DbConnection)(object)val).Open();
			DateTime queryTime = DateTime.Now.AddDays(-1 * beforedays);
			int queryPercent = percent;
			string text = "SELECT * FROM BatteryReportData WHERE DTIME <= @now";
			DynamicParameters val2 = new DynamicParameters();
			val2.Add("now", (object)DateTime.Now, (DbType?)DbType.DateTime, (ParameterDirection?)null, (int?)null, (byte?)null, (byte?)null);
			IEnumerable<ReportData> source = SqlMapper.Query<ReportData>((IDbConnection)val, text, (object)val2, (IDbTransaction)null, true, (int?)null, (CommandType?)null);
			IEnumerable<ReportData> source2 = source.Where((ReportData n) => (n.DTIME >= queryTime) & (n.PERCENT <= queryPercent));
			if (source2.ToList().Count > 0)
			{
				return (DateTime.Now - source2.Max((ReportData n) => n.DTIME)).Days;
			}
			IEnumerable<ReportData> source3 = source.Where((ReportData n) => n.PERCENT <= queryPercent);
			if (source3.ToList().Count > 0)
			{
				return (DateTime.Now - source3.Max((ReportData n) => n.DTIME)).Days;
			}
			return (DateTime.Now - source.Min((ReportData n) => n.DTIME)).Days;
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void InitSQLiteDb()
	{
		//IL_0014: Unknown result type (might be due to invalid IL or missing references)
		//IL_001a: Expected O, but got Unknown
		if (File.Exists(dbPath))
		{
			return;
		}
		SQLiteConnection val = new SQLiteConnection(cnStr);
		try
		{
			SqlMapper.Execute((IDbConnection)val, "\r\n                    CREATE TABLE BatteryReportData (\r\n                        ID VARCHAR(16),\r\n                        DTIME DateTime,\r\n                        STATE VARCHAR(32),\r\n                        SOURCE VARCHAR(32),\r\n                        PERCENT Integer,\r\n                        CAPAC VARCHAR(32),\r\n                        CONSTRAINT ReportData_PK PRIMARY KEY (Id)\r\n                    )", (object)null, (IDbTransaction)null, (int?)null, (CommandType?)null);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void CheckDate()
	{
		//IL_0006: Unknown result type (might be due to invalid IL or missing references)
		//IL_000c: Expected O, but got Unknown
		//IL_0018: Unknown result type (might be due to invalid IL or missing references)
		//IL_0036: Expected O, but got Unknown
		SQLiteConnection val = new SQLiteConnection(cnStr);
		try
		{
			((DbConnection)(object)val).Open();
			SqlMapper.Query<ReportData>((IDbConnection)val, "select * from BatteryReportData", (object)new DynamicParameters(), (IDbTransaction)null, true, (int?)null, (CommandType?)null);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void AsnycDataBase()
	{
		//IL_0006: Unknown result type (might be due to invalid IL or missing references)
		//IL_000c: Expected O, but got Unknown
		//IL_0018: Unknown result type (might be due to invalid IL or missing references)
		//IL_001e: Expected O, but got Unknown
		SQLiteConnection val = new SQLiteConnection(cnStr);
		try
		{
			((DbConnection)(object)val).Open();
			string text = "SELECT * FROM BatteryReportData WHERE DTIME <= @now";
			DynamicParameters val2 = new DynamicParameters();
			val2.Add("now", (object)DateTime.Now, (DbType?)DbType.DateTime, (ParameterDirection?)null, (int?)null, (byte?)null, (byte?)null);
			IEnumerable<ReportData> source = SqlMapper.Query<ReportData>((IDbConnection)val, text, (object)val2, (IDbTransaction)null, true, (int?)null, (CommandType?)null);
			if (source.ToList().Count == 0)
			{
				foreach (ReportData item in OSDailyReport.Values.ToList())
				{
					string text2 = "INSERT INTO BatteryReportData (ID,DTIME,STATE,SOURCE,PERCENT,CAPAC) VALUES(@ID,@DTIME,@STATE,@SOURCE,@PERCENT,@CAPAC)";
					try
					{
						SqlMapper.Execute((IDbConnection)val, text2, (object)item, (IDbTransaction)null, (int?)null, (CommandType?)null);
					}
					catch (Exception)
					{
					}
				}
				return;
			}
			foreach (KeyValuePair<string, ReportData> ositem in OSDailyReport)
			{
				if ((from n in source.ToList()
					where n.ID == ositem.Value.ID
					select n).Count() != 0)
				{
					if (!source.Single((ReportData n) => n.ID == ositem.Value.ID).PERCENT.Equals(ositem.Value.PERCENT))
					{
						SqlMapper.Execute((IDbConnection)val, "update BatteryReportData set ID = @ID,DTIME = @DTIME,STATE = @STATE,PERCENT = @PERCENT ,CAPAC = @CAPAC where ID=" + ositem.Value.ID, (object)ositem.Value, (IDbTransaction)null, (int?)null, (CommandType?)null);
					}
					continue;
				}
				string text3 = "INSERT INTO BatteryReportData (ID,DTIME,STATE,SOURCE,PERCENT,CAPAC) VALUES(@ID,@DTIME,@STATE,@SOURCE,@PERCENT,@CAPAC)";
				try
				{
					SqlMapper.Execute((IDbConnection)val, text3, (object)ositem.Value, (IDbTransaction)null, (int?)null, (CommandType?)null);
				}
				catch (Exception)
				{
				}
			}
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void BatteryReportFromOS()
	{
		try
		{
			Process process = new Process();
			ProcessStartInfo processStartInfo = new ProcessStartInfo
			{
				WindowStyle = ProcessWindowStyle.Hidden,
				FileName = "powercfg"
			};
			process.StartInfo = processStartInfo;
			processStartInfo.Arguments = "-batteryreport -duration 14";
			processStartInfo.RedirectStandardOutput = true;
			processStartInfo.WorkingDirectory = path;
			process.StartInfo.UseShellExecute = false;
			process.StartInfo.CreateNoWindow = true;
			process.Start();
		}
		catch
		{
		}
		int num = 0;
		while (num < 10 && !File.Exists(ReportPath))
		{
			num++;
			Thread.Sleep(500);
		}
		File.Exists(ReportPath);
	}
}
