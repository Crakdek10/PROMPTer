export function pcm16ToBase64(pcm16: Int16Array): string {
  const u8 = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength);
  let bin = "";
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin);
}
