import {Composition} from 'remotion';
import {VidrushVideo, varsayilanProps, VideoProps} from './Video';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VidrushVideo"
      component={VidrushVideo}
      durationInFrames={150}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={varsayilanProps}
      calculateMetadata={({props}) => {
        const p = props as VideoProps;
        const toplam = p.sahneler.reduce(
          (a, s) => a + Math.max(1, Math.round(s.sure * p.fps)),
          0
        );
        return {
          durationInFrames: Math.max(30, toplam),
          fps: p.fps,
          width: p.genislik,
          height: p.yukseklik,
        };
      }}
    />
  );
};
