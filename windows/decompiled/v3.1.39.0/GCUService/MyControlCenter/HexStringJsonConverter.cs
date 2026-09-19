using System;
using Newtonsoft.Json;

namespace MyControlCenter;

public sealed class HexStringJsonConverter : JsonConverter
{
	public override bool CanConvert(Type objectType)
	{
		return typeof(uint).Equals(objectType);
	}

	public override void WriteJson(JsonWriter writer, object value, JsonSerializer serializer)
	{
		writer.WriteValue($"0x{value:X2}");
	}

	public override object ReadJson(JsonReader reader, Type objectType, object existingValue, JsonSerializer serializer)
	{
		string text = reader.ReadAsString();
		if (text == null || !text.StartsWith("0x"))
		{
			throw new JsonSerializationException();
		}
		return Convert.ToUInt32(text);
	}
}
