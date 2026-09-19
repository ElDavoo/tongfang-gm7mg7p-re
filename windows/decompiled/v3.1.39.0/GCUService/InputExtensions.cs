using System.Collections.Generic;

public static class InputExtensions
{
	public static int LimitToRange(this int value, int inclusiveMinimum, int inclusiveMaximum)
	{
		if (value < inclusiveMinimum)
		{
			return inclusiveMinimum;
		}
		if (value > inclusiveMaximum)
		{
			return inclusiveMaximum;
		}
		return value;
	}

	public static uint LimitToRange(this uint value, uint inclusiveMinimum, uint inclusiveMaximum)
	{
		if (value < inclusiveMinimum)
		{
			return inclusiveMinimum;
		}
		if (value > inclusiveMaximum)
		{
			return inclusiveMaximum;
		}
		return value;
	}

	public static uint CheckIntegrityValue(this uint value, uint defaultvalue, List<uint> items)
	{
		foreach (uint item in items)
		{
			if (value == item)
			{
				return value;
			}
		}
		return defaultvalue;
	}
}
