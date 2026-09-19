using System;
using System.Collections.Generic;
using System.Linq;

namespace GCUService.MyRgbKeyboard;

public static class EnumHelper
{
	public static List<T> ToList<T>()
	{
		return Enum.GetValues(typeof(T)).Cast<T>().ToList();
	}

	public static IEnumerable<T> ToEnumerable<T>()
	{
		return Enum.GetValues(typeof(T)).Cast<T>();
	}
}
