using System;
using System.Linq;
using Newtonsoft.Json;

namespace MyControlCenter;

public class ByteArrayHexConverter : JsonConverter
{
	private readonly string _separator;

	public override bool CanConvert(Type objectType)
	{
		return objectType == typeof(byte[]);
	}

	public override object ReadJson(JsonReader reader, Type objectType, object existingValue, JsonSerializer serializer)
	{
		if (reader.TokenType == JsonToken.String)
		{
			string hex = serializer.Deserialize<string>(reader);
			if (!string.IsNullOrEmpty(hex))
			{
				return (from x in Enumerable.Range(0, hex.Length)
					where x % 2 == 0
					select Convert.ToByte(hex.Substring(x, 2), 16)).ToArray();
			}
		}
		return Enumerable.Empty<byte>();
	}

	public ByteArrayHexConverter(string separator = ",")
	{
		_separator = separator;
	}

	public ByteArrayHexConverter()
	{
		_separator = ",";
	}

	public override void WriteJson(JsonWriter writer, object value, JsonSerializer serializer)
	{
		string value2 = string.Join(_separator, ((byte[])value).Select((byte p) => p.ToString("X2")));
		writer.WriteValue(value2);
	}
}
