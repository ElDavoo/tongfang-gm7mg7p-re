using System;

namespace Utility;

public static class Time
{
	private static DateTime epoch = new DateTime(1970, 1, 1);

	public static long GetSecondsSinceEpoch()
	{
		return (long)(DateTime.Now - epoch).TotalSeconds;
	}

	public static long GetMillisecondsSinceEpoch()
	{
		return (long)(DateTime.Now - epoch).TotalMilliseconds;
	}

	public static int GetMilliSeconds()
	{
		return DateTime.Now.Millisecond;
	}

	public static int GetSeconds()
	{
		return DateTime.Now.Second;
	}

	public static int GetHours()
	{
		return DateTime.Now.Hour;
	}

	public static int GetMinutes()
	{
		return DateTime.Now.Minute;
	}

	public static bool IsCurrentTimeBetween(int start_hour, int end_hour)
	{
		return IsCurrentTimeBetween(new TimeSpan(start_hour, 0, 0), new TimeSpan(end_hour, 0, 0));
	}

	public static bool IsCurrentTimeBetween(int start_hour, int start_minute, int end_hour, int end_minute)
	{
		return IsCurrentTimeBetween(new TimeSpan(start_hour, start_minute, 0), new TimeSpan(end_hour, end_minute, 0));
	}

	public static bool IsCurrentTimeBetween(TimeSpan start, TimeSpan end)
	{
		TimeSpan timeOfDay = DateTime.Now.TimeOfDay;
		if (start < end)
		{
			if (start <= timeOfDay)
			{
				return timeOfDay <= end;
			}
			return false;
		}
		if (end < timeOfDay)
		{
			return !(timeOfDay < start);
		}
		return true;
	}
}
