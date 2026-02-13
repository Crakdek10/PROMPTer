export {};

declare global {
  interface Window {
    prompter: {
      ping: () => string;
      minimize: () => void;
      maximize: () => void;
      close: () => void;

      listSystemAudioSources: () => Promise<Array<{ id: string; name: string }>>;
      setWindowOpacity: (value01: number) => void;
    };
  }
}
